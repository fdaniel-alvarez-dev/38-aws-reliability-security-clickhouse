#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def fail(message: str, *, output: str | None = None, code: int = 1) -> None:
    print(f"FAIL: {message}")
    if output:
        print(output.rstrip())
    raise SystemExit(code)


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        fail(f"Missing {description}: {path}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON: {path}", output=str(exc))
    return {}


def _http(base_url: str, *, query: str | None = None, timeout_s: int = 5) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        fail("CLICKHOUSE_HTTP_URL must be http:// or https://", code=2)

    q = dict(parse_qsl(parsed.query))
    if query is not None:
        q["query"] = query
    final = urlunparse(parsed._replace(query=urlencode(q)))

    req = Request(final, method="POST" if query else "GET")
    with urlopen(req, timeout=timeout_s) as resp:
        body = resp.read()
    return body.decode("utf-8", errors="replace")


def demo_mode() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    report_path = ARTIFACTS_DIR / "clickhouse_guardrails.json"
    guard = run([sys.executable, "tools/clickhouse_guardrails.py", "--format", "json", "--out", str(report_path)])
    if guard.returncode != 0:
        fail("ClickHouse guardrails failed (demo mode must be offline).", output=guard.stdout)

    report = load_json(report_path)
    if report.get("summary", {}).get("errors", 0) != 0:
        fail("ClickHouse guardrails reported errors.", output=json.dumps(report.get("findings", []), indent=2))

    demo = run([sys.executable, "pipelines/pipeline_demo.py"])
    if demo.returncode != 0:
        fail("Offline demo pipeline failed.", output=demo.stdout)

    out_path = REPO_ROOT / "data" / "processed" / "events_jsonl" / "events.jsonl"
    require_file(out_path, "offline demo output")
    if out_path.stat().st_size == 0:
        fail("Offline demo output is empty.", output=str(out_path))

    for required in ["NOTICE.md", "COMMERCIAL_LICENSE.md", "GOVERNANCE.md"]:
        require_file(REPO_ROOT / required, required)

    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8", errors="replace")
    if "it.freddy.alvarez@gmail.com" not in license_text:
        fail("LICENSE must include the commercial licensing contact email.")

    print("OK: demo-mode tests passed (offline).")


def production_mode() -> None:
    if os.environ.get("PRODUCTION_TESTS_CONFIRM") != "1":
        fail(
            "Production-mode tests require an explicit opt-in.",
            output=(
                "Set `PRODUCTION_TESTS_CONFIRM=1` and rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    ran_external_integration = False

    ch_url = os.environ.get("CLICKHOUSE_HTTP_URL", "").strip()
    if ch_url:
        try:
            pong = _http(ch_url.rstrip("/") + "/ping")
            if "Ok" not in pong:
                raise RuntimeError(f"unexpected ping response: {pong!r}")
            out = _http(ch_url, query="SELECT 1 FORMAT TabSeparated")
            if out.strip() != "1":
                raise RuntimeError(f"unexpected SELECT 1 output: {out!r}")
        except Exception as exc:
            fail(
                "ClickHouse HTTP integration failed.",
                output=(
                    "Verify CLICKHOUSE_HTTP_URL is reachable and credentials (if any) are present in the URL query.\n"
                    "Example:\n"
                    "  CLICKHOUSE_HTTP_URL='http://localhost:8123'\\\n"
                    "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n\n"
                    f"{type(exc).__name__}: {exc}\n"
                ),
            )

        ran_external_integration = True

        if os.environ.get("CLICKHOUSE_WRITE_TESTS") == "1":
            db = os.environ.get("CLICKHOUSE_TEST_DB", "").strip()
            if not db:
                fail(
                    "CLICKHOUSE_WRITE_TESTS=1 requires CLICKHOUSE_TEST_DB.",
                    output=(
                        "Set CLICKHOUSE_TEST_DB to an isolated database name and rerun.\n"
                        "Example:\n"
                        "  CLICKHOUSE_WRITE_TESTS=1 CLICKHOUSE_TEST_DB=clickhouse_guardrails_test\n"
                    ),
                    code=2,
                )

            events = REPO_ROOT / "data" / "processed" / "events_jsonl" / "events.jsonl"
            if not events.exists():
                fail(
                    "Write tests require the demo dataset to be created first.",
                    output="Run demo mode once: TEST_MODE=demo python3 tests/run_tests.py",
                    code=2,
                )

            _http(ch_url, query=f"CREATE DATABASE IF NOT EXISTS {db}")
            _http(
                ch_url,
                query=(
                    f"CREATE TABLE IF NOT EXISTS {db}.events ("
                    "event_id UInt64, user_id UInt64, event_type String, event_ts String"
                    ") ENGINE=MergeTree ORDER BY (event_type, event_id)"
                ),
            )
            _http(ch_url, query=f"TRUNCATE TABLE {db}.events")

            data = events.read_text(encoding='utf-8', errors='replace').encode("utf-8")
            parsed = urlparse(ch_url)
            q = dict(parse_qsl(parsed.query))
            q["query"] = f"INSERT INTO {db}.events FORMAT JSONEachRow"
            final = urlunparse(parsed._replace(query=urlencode(q)))
            req = Request(final, data=data, method="POST")
            with urlopen(req, timeout=10) as resp:
                resp.read()

            count = _http(ch_url, query=f"SELECT count() FROM {db}.events FORMAT TabSeparated").strip()
            if int(count) <= 0:
                fail("Write test inserted zero rows.", output=f"count={count}")

    if os.environ.get("TERRAFORM_VALIDATE") == "1":
        tf = shutil.which("terraform")
        if tf is None:
            fail(
                "TERRAFORM_VALIDATE=1 requires terraform.",
                output="Install Terraform and rerun production mode, or unset TERRAFORM_VALIDATE.",
                code=2,
            )
        ran_external_integration = True
        example_dir = REPO_ROOT / "infra" / "examples" / "dev"
        init = run([tf, "init", "-backend=false"], cwd=example_dir)
        if init.returncode != 0:
            fail("terraform init failed.", output=init.stdout, code=2)
        validate = run([tf, "validate"], cwd=example_dir)
        if validate.returncode != 0:
            fail("terraform validate failed.", output=validate.stdout)

    if not ran_external_integration:
        fail(
            "No external integration checks were executed in production mode.",
            output=(
                "Enable at least one real integration:\n"
                "- Set `CLICKHOUSE_HTTP_URL` to run ClickHouse HTTP `/ping` + `SELECT 1`, and/or\n"
                "- Set `TERRAFORM_VALIDATE=1` to run Terraform validate.\n\n"
                "Then rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    print("OK: production-mode tests passed (integrations executed).")


def main() -> None:
    mode = os.environ.get("TEST_MODE", "demo").strip().lower()
    if mode not in {"demo", "production"}:
        fail("Invalid TEST_MODE. Expected 'demo' or 'production'.", code=2)

    if mode == "demo":
        demo_mode()
        return

    production_mode()


if __name__ == "__main__":
    main()
