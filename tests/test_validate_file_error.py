# tests/test_validate_file_error.py
from pathlib import Path

from src.tool.validate import run_validate


def test_validate_writes_file_error_on_no_header(tmp_path: Path):
    input_csv = tmp_path / "broken.csv"
    input_csv.write_text("", encoding="utf-8")  # 空 = ヘッダー無し

    errors_csv = tmp_path / "errors.csv"

    code = run_validate(input_csv, errors_csv)

    assert code == 2
    txt = errors_csv.read_text(encoding="utf-8")
    assert "file_error:" in txt
    assert "CSV has no header row" in txt