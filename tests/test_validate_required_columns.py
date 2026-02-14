# tests/test_validate_required_columns.py
from src.tool.validate import validate_required_columns


def test_validate_required_columns_detects_missing_process():
    rows = [
        {"date": "2026-02-13", "process": "ミキサー準備", "operator": "A"},
        {"date": "2026-02-13", "process": "", "operator": "A"},
    ]

    errors = validate_required_columns(rows)

    assert len(errors) == 1
    assert errors[0].row_number == 3  # rowsはデータ行扱いで start=2 → 2行目はCSV上3行目
    assert "missing_required" in errors[0].reason
    assert "process" in errors[0].reason
