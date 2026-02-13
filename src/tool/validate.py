from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import logging

logger = logging.getLogger("worklog_tool")

REQUIRED_COLUMNS = ["date", "process", "operator"]


@dataclass
class RowError:
    row_number: int           # CSVの行番号（ヘッダー=1として、データは2〜）
    reason: str
    raw: dict[str, str]


def read_csv_utf8(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row.")
        return list(reader)


def validate_required_columns(rows: list[dict[str, str]]) -> list[RowError]:
    errors: list[RowError] = []
    # DictReader は存在しない列でも key を作らないので、各行で get() する
    for i, row in enumerate(rows, start=2):
        missing = [c for c in REQUIRED_COLUMNS if not (row.get(c) or "").strip()]
        if missing:
            errors.append(RowError(i, f"missing_required: {','.join(missing)}", row))
    return errors

def validate_time_rules(rows: list[dict[str, str]]) -> list[RowError]:
    """
    Rule:
      - Either (start and end) are both present and valid HH:MM
      - OR minutes is present and valid integer > 0
    """
    errors: list[RowError] = []

    def is_hhmm(s: str) -> bool:
        s = (s or "").strip()
        if len(s) != 5 or s[2] != ":":
            return False
        hh, mm = s.split(":")
        if not (hh.isdigit() and mm.isdigit()):
            return False
        h = int(hh)
        m = int(mm)
        return 0 <= h <= 23 and 0 <= m <= 59

    def parse_pos_int(s: str) -> int | None:
        s = (s or "").strip()
        if not s:
            return None
        if not s.isdigit():
            return -1
        v = int(s)
        return v

    for i, row in enumerate(rows, start=2):
        start = (row.get("start") or "").strip()
        end = (row.get("end") or "").strip()
        minutes_raw = (row.get("minutes") or "").strip()

        has_start = bool(start)
        has_end = bool(end)
        has_minutes = bool(minutes_raw)

        # minutes があれば minutes方式を優先（start/endが多少入っていても後で調整可能）
        if has_minutes:
            v = parse_pos_int(minutes_raw)
            if v is None:
                pass
            elif v <= 0:
                errors.append(RowError(i, "minutes_invalid: must be integer > 0", row))
            return_minutes_invalid = False
            if v == -1:
                errors.append(RowError(i, "minutes_invalid: not an integer", row))
            continue

        # minutes が無い場合は start/end の両方が必要
        if has_start or has_end:
            if not (has_start and has_end):
                errors.append(RowError(i, "time_incomplete: need both start and end", row))
                continue
            if not is_hhmm(start):
                errors.append(RowError(i, "start_invalid: expected HH:MM", row))
                continue
            if not is_hhmm(end):
                errors.append(RowError(i, "end_invalid: expected HH:MM", row))
                continue
            continue

        # start/end/minutes 全部ない
        errors.append(RowError(i, "time_missing: provide start+end OR minutes", row))

    return errors


def write_errors_csv(path: Path, errors: Iterable[RowError]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row_number", "reason", "raw"])
        for e in errors:
            writer.writerow([e.row_number, e.reason, e.raw])


def run_validate(input_csv: Path, errors_csv: Path) -> int:
    logger.info(f"validate: start input={input_csv}")

    rows = read_csv_utf8(input_csv)

    errors: list[RowError] = []
    errors.extend(validate_required_columns(rows))
    errors.extend(validate_time_rules(rows))

    write_errors_csv(errors_csv, errors)

    logger.info(f"validate: rows={len(rows)} errors={len(errors)} errors_csv={errors_csv}")

    if errors:
        print(f"INVALID: {len(errors)} error(s). -> {errors_csv}")
        logger.info("validate: finished status=INVALID")
        return 2

    print("VALID: no errors.")
    logger.info("validate: finished status=VALID")
    return 0


