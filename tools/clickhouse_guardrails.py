#!/usr/bin/env python3
import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Finding:
    severity: str  # ERROR | WARN | INFO
    rule_id: str
    message: str
    path: str | None = None


def add(findings: list[Finding], severity: str, rule_id: str, message: str, path: Path | None = None) -> None:
    findings.append(
        Finding(
            severity=severity,
            rule_id=rule_id,
            message=message,
            path=str(path.relative_to(REPO_ROOT)) if path else None,
        )
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def summarize(findings: list[Finding]) -> dict:
    return {
        "errors": sum(1 for f in findings if f.severity == "ERROR"),
        "warnings": sum(1 for f in findings if f.severity == "WARN"),
        "info": sum(1 for f in findings if f.severity == "INFO"),
    }


def check_readme_is_generic(findings: list[Finding]) -> None:
    readme = REPO_ROOT / "README.md"
    if not readme.exists():
        add(findings, "ERROR", "docs.readme", "README.md is missing.", readme)
        return
    text = read_text(readme)
    if re.search(r"(?i)job-boards\\.greenhouse\\.io|\\bgh_jid\\b", text):
        add(findings, "ERROR", "docs.branding", "README contains job-posting identifiers; keep it generic.", readme)


def check_demo_tests_workflow(findings: list[Finding]) -> None:
    wf = REPO_ROOT / ".github" / "workflows" / "tests.yml"
    if not wf.exists():
        add(findings, "WARN", "ci.demo_tests", "Add a CI workflow to run demo-mode tests.", wf)
        return
    text = read_text(wf)
    if "TEST_MODE" not in text or "demo" not in text:
        add(findings, "WARN", "ci.demo_tests", "tests.yml should run TEST_MODE=demo.", wf)


def check_gitignore(findings: list[Finding]) -> None:
    ignore = REPO_ROOT / ".gitignore"
    if not ignore.exists():
        add(findings, "ERROR", "gitignore.missing", ".gitignore is missing.", ignore)
        return
    text = read_text(ignore)
    required = ["artifacts/", "data/processed/", ".[0-9][0-9]_*.txt", "*.pyc"]
    for r in required:
        if r not in text:
            add(findings, "WARN", "gitignore.rule", f"Consider adding gitignore rule: {r}", ignore)


def check_clickhouse_notes(findings: list[Finding]) -> None:
    readme = REPO_ROOT / "README.md"
    if not readme.exists():
        return
    text = read_text(readme)
    if "ClickHouse" not in text and "clickhouse" not in text:
        add(findings, "WARN", "docs.clickhouse", "README should mention ClickHouse and how validations are performed safely.", readme)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline ClickHouse governance guardrails for this repo.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--out", default="", help="Write output to a file (optional).")
    args = parser.parse_args()

    findings: list[Finding] = []
    check_readme_is_generic(findings)
    check_demo_tests_workflow(findings)
    check_gitignore(findings)
    check_clickhouse_notes(findings)

    report = {"summary": summarize(findings), "findings": [asdict(f) for f in findings]}
    if args.format == "json":
        output = json.dumps(report, indent=2, sort_keys=True)
    else:
        lines = []
        for f in findings:
            where = f" ({f.path})" if f.path else ""
            lines.append(f"{f.severity} {f.rule_id}{where}: {f.message}")
        lines.append("")
        lines.append(f"Summary: {report['summary']}")
        output = "\n".join(lines)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
