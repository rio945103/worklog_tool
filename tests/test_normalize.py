# tests/test_normalize.py
from pathlib import Path

from src.tool.build import run_build
from src.tool.normalize import normalize_row
from src.tool.validate import RowError


def test_normalize_row_minutes_priority():
    """minutes方式が優先される（start/endがあっても無視）"""
    row = {
        "date": "2026-02-13",
        "process": "テスト工程",
        "operator": "A",
        "start": "09:00",
        "end": "10:00",
        "minutes": "30",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert len(errors) == 0
    assert norm_row is not None
    assert norm_row.minutes == 30  # minutesが優先される（start/endの60分ではない）


def test_normalize_row_start_end_calculates_minutes():
    """start/end方式でminutesが正しく算出される"""
    row = {
        "date": "2026-02-13",
        "process": "テスト工程",
        "operator": "A",
        "start": "09:00",
        "end": "09:45",
        "minutes": "",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert len(errors) == 0
    assert norm_row is not None
    assert norm_row.minutes == 45  # 09:00から09:45まで45分


def test_normalize_row_day_overflow_allowed():
    """日跨ぎが許可されている（end < startの場合）"""
    row = {
        "date": "2026-02-13",
        "process": "テスト工程",
        "operator": "A",
        "start": "23:00",
        "end": "01:00",
        "minutes": "",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert len(errors) == 0
    assert norm_row is not None
    # 23:00から01:00まで = (24*60 - 1380) + 60 = 120分（2時間）
    assert norm_row.minutes == 120


def test_normalize_row_invalid_date_format():
    """無効な日付形式でエラー"""
    row = {
        "date": "2026/02/13",  # 無効な形式
        "process": "テスト工程",
        "operator": "A",
        "start": "09:00",
        "end": "09:45",
        "minutes": "",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert norm_row is None
    assert len(errors) == 1
    assert "date_invalid" in errors[0].reason


def test_normalize_row_negative_minutes_error():
    """負のminutesでエラー"""
    row = {
        "date": "2026-02-13",
        "process": "テスト工程",
        "operator": "A",
        "start": "",
        "end": "",
        "minutes": "-10",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert norm_row is None
    assert len(errors) == 1
    assert "minutes_invalid" in errors[0].reason


def test_normalize_row_invalid_minutes_format():
    """無効なminutes形式でエラー"""
    row = {
        "date": "2026-02-13",
        "process": "テスト工程",
        "operator": "A",
        "start": "",
        "end": "",
        "minutes": "abc",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert norm_row is None
    assert len(errors) == 1
    assert "minutes_invalid" in errors[0].reason
    assert "not an integer" in errors[0].reason


def test_normalize_row_missing_time_error():
    """start/end/minutes全部ない場合エラー"""
    row = {
        "date": "2026-02-13",
        "process": "テスト工程",
        "operator": "A",
        "start": "",
        "end": "",
        "minutes": "",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert norm_row is None
    assert errors == []  # 時間欠損の判定は validate が担当（normalize は追加エラーを出さない）


def test_normalize_row_invalid_start_format():
    """無効なstart形式でエラー"""
    row = {
        "date": "2026-02-13",
        "process": "テスト工程",
        "operator": "A",
        "start": "xx:yy",
        "end": "09:45",
        "minutes": "",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert norm_row is None
    assert len(errors) == 1
    assert "start_invalid" in errors[0].reason


def test_normalize_row_invalid_end_format():
    """無効なend形式でエラー"""
    row = {
        "date": "2026-02-13",
        "process": "テスト工程",
        "operator": "A",
        "start": "09:00",
        "end": "25:00",  # 無効な時刻
        "minutes": "",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert norm_row is None
    assert len(errors) == 1
    assert "end_invalid" in errors[0].reason


def test_normalize_row_same_start_end_error():
    """startとendが同じ場合エラー（diff <= 0）"""
    row = {
        "date": "2026-02-13",
        "process": "テスト工程",
        "operator": "A",
        "start": "09:00",
        "end": "09:00",
        "minutes": "",
        "note": "test",
    }
    
    norm_row, errors = normalize_row(2, row)
    
    assert norm_row is None
    assert len(errors) == 1
    assert "time_order_invalid" in errors[0].reason


def test_build_with_errors_writes_errors_csv(tmp_path: Path):
    """エラーがある場合、errors.csvに出力される"""
    input_csv = tmp_path / "in.csv"
    input_csv.write_text(
        "\n".join(
            [
                "date,start,end,process,operator,minutes,note",
                "2026-02-13,09:00,09:40,ミキサー準備,A,,test",  # OK
                "2026-02-13,xx:yy,09:40,ミキサー準備,A,,test",  # エラー: 無効なstart
                "2026-02-13,,,ミキサー準備,A,,test",  # エラー: time_missing
            ]
        ),
        encoding="utf-8",
    )
    
    out_dir = tmp_path / "reports"
    
    code = run_build(input_csv, out_dir)
    
    # エラーがあるので終了コードは2
    assert code == 2
    
    # errors.csvが存在する
    errors_csv = out_dir / "errors.csv"
    assert errors_csv.exists()
    
    errors_content = errors_csv.read_text(encoding="utf-8")
    assert "start_invalid" in errors_content or "time_missing" in errors_content
    
    # 有効な行は処理される
    daily = (out_dir / "summary_daily.csv").read_text(encoding="utf-8")
    assert "2026-02-13,40,1" in daily



