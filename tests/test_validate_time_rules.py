# tests/test_validate_time_rules.py
from src.tool.validate import validate_time_rules


def test_validate_time_rules_incomplete_time_detected():
    rows = [
        # OK: start+end
        {"date": "2026-02-13", "start": "09:00", "end": "09:10", "minutes": ""},
        # NG: end欠損
        {"date": "2026-02-13", "start": "09:00", "end": "", "minutes": ""},
    ]

    errors = validate_time_rules(rows)

    assert len(errors) == 1
    assert errors[0].row_number == 3  # 2行目のデータ → CSV上3行目
    assert errors[0].reason.startswith("time_incomplete")
