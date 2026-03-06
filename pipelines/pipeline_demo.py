from __future__ import annotations

import csv
from pathlib import Path


ALLOWED_EVENT_TYPES = {"signup", "login", "purchase"}


def validate_row(row: dict[str, str], *, line_no: int) -> None:
    def must_int_ge_1(field: str) -> None:
        raw = (row.get(field) or "").strip()
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"line {line_no}: {field} must be an integer (got {raw!r})") from exc
        if value < 1:
            raise ValueError(f"line {line_no}: {field} must be >= 1 (got {value})")

    must_int_ge_1("event_id")
    must_int_ge_1("user_id")

    event_type = (row.get("event_type") or "").strip()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"line {line_no}: event_type must be one of {sorted(ALLOWED_EVENT_TYPES)} (got {event_type!r})")

    event_ts = (row.get("event_ts") or "").strip()
    if not event_ts:
        raise ValueError(f"line {line_no}: event_ts must be non-empty")


def main() -> None:
    raw_path = Path("data/raw/events.csv")
    out_dir = Path("data/processed/events_jsonl")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "events.jsonl"

    if not raw_path.exists():
        raise SystemExit(f"Missing input file: {raw_path}")

    with raw_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit("CSV has no header row.")

        missing = [c for c in ["event_id", "user_id", "event_type", "event_ts"] if c not in reader.fieldnames]
        if missing:
            raise SystemExit(f"CSV missing required columns: {missing}")

        count = 0
        with out_path.open("w", encoding="utf-8", newline="\n") as out:
            for idx, row in enumerate(reader, start=2):
                validate_row(row, line_no=idx)
                out.write(
                    f'{{"event_id":{int(row["event_id"])},'
                    f'"user_id":{int(row["user_id"])},'
                    f'"event_type":"{row["event_type"]}",'
                    f'"event_ts":"{row["event_ts"]}"}}\n'
                )
                count += 1

    print(f"Wrote {out_path} ({count} rows)")


if __name__ == "__main__":
    main()
