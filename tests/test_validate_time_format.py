# tests/test_validate_time_format.py
from src.tool.validate import validate_time_rules


def test_validate_time_rules_invalid_start_format_detected():
    rows = [
        # NG: start不正（HH:MMではない）
        {"date": "2026-02-13", "start": "xx:yy", "end": "10:00", "minutes": ""},
    ]

    errors = validate_time_rules(rows)

    assert len(errors) == 1
    assert errors[0].row_number == 2  # 1行目データ → CSV上2行目
    assert errors[0].reason.startswith("start_invalid")
