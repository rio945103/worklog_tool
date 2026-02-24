# src/tool/validate.py
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

logger = logging.getLogger("worklog_tool")

REQUIRED_COLUMNS = ["date", "process", "operator"]


@dataclass
class RowError:
    row_number: int  # CSVの行番号（ヘッダー=1として、データは2〜。file_errorは0）
    reason: str
    raw: dict[str, str]


def read_csv_utf8(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row.")
        fieldnames = [h.strip() for h in reader.fieldnames]
        return fieldnames, list(reader)


def validate_header(fieldnames: list[str]) -> list[RowError]:
    missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
    if not missing:
        return []
    return [
        RowError(
            row_number=0,
            reason=f"file_error: missing_columns: {','.join(missing)}",
            raw={"header": ",".join(fieldnames)},
        )
    ]


def validate_required_columns(rows: list[dict[str, str]]) -> list[RowError]:
    errors: list[RowError] = []
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

    for i, row in enumerate(rows, start=2):
        start = (row.get("start") or "").strip()
        end = (row.get("end") or "").strip()
        minutes_raw = (row.get("minutes") or "").strip()

        # minutes方式があれば優先
        if minutes_raw:
            if not minutes_raw.isdigit():
                errors.append(RowError(i, "minutes_invalid: not an integer", row))
                continue
            v = int(minutes_raw)
            if v <= 0:
                errors.append(RowError(i, "minutes_invalid: must be integer > 0", row))
            continue

        has_start = bool(start)
        has_end = bool(end)

        # minutesが無い場合は start/end の両方が必要
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

    try:
        fieldnames, rows = read_csv_utf8(input_csv)

        header_errors = validate_header(fieldnames)
        if header_errors:
            write_errors_csv(errors_csv, header_errors)
            logger.info(f"validate: header_error errors={len(header_errors)} errors_csv={errors_csv}")
            print(f"INVALID: header_error -> {errors_csv}")
            logger.info("validate: finished status=INVALID")
            return 2

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

    except Exception as e:
        file_error = RowError(
            row_number=0,
            reason=f"file_error: {type(e).__name__}: {e}",
            raw={"input": str(input_csv)},
        )
        write_errors_csv(errors_csv, [file_error])

        logger.exception(f"validate: file_error input={input_csv}")
        print(f"INVALID: file_error -> {errors_csv}")
        return 2