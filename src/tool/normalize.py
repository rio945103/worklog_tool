# src/tool/normalize.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .validate import RowError


@dataclass
class NormalizedRow:
    date: str
    process: str
    operator: str
    minutes: int
    note: str


def _parse_date_yyyy_mm_dd(s: str) -> bool:
    """日付文字列がYYYY-MM-DD形式かチェック"""
    s = (s or "").strip()
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _parse_minutes(s: str) -> int | None:
    """
    minutes文字列をパース
    Returns:
        int: 有効な正の整数
        None: 空欄
        -1: 整数ではない
    """
    s = (s or "").strip()
    if not s:
        return None
    if not s.isdigit():
        return -1
    return int(s)


def _parse_hhmm_to_minutes(s: str) -> int | None:
    """
    HH:MM形式の時刻文字列を分に変換
    Returns:
        int: 0-1439の範囲の分（0:00=0, 23:59=1439）
        None: 無効な形式
    """
    s = (s or "").strip()
    if len(s) != 5 or s[2] != ":":
        return None
    hh, mm = s.split(":")
    if not (hh.isdigit() and mm.isdigit()):
        return None
    h = int(hh)
    m = int(mm)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return h * 60 + m


def normalize_row(row_number: int, row: dict[str, str]) -> tuple[NormalizedRow | None, list[RowError]]:
    """
    1行を正規化してNormalizedRowに変換
    
    validate_time_rules()と矛盾しない挙動を保証：
    - minutes方式: minutesが優先（start/endがあっても無視）
    - start/end方式: 差分からminutes算出（日跨ぎを許可）
    
    Args:
        row_number: CSVの行番号（ヘッダー=1として、データは2〜）
        row: CSV行の辞書
        
    Returns:
        (NormalizedRow | None, list[RowError]): 
            - 正規化成功時: (NormalizedRow, [])
            - エラー時: (None, [RowError, ...])
    """
    errors: list[RowError] = []
    
    # 必須フィールドの取得
    date = (row.get("date") or "").strip()
    process = (row.get("process") or "").strip()
    operator = (row.get("operator") or "").strip()
    note = (row.get("note") or "").strip()
    
    # date形式チェック
    if not _parse_date_yyyy_mm_dd(date):
        errors.append(RowError(row_number, "date_invalid: expected YYYY-MM-DD", row))
        return None, errors
    
    # minutes方式の処理（validate_time_rules()と同様に優先）
    minutes_raw = (row.get("minutes") or "").strip()
    if minutes_raw:
        m = _parse_minutes(minutes_raw)
        if m is None:
            # 空欄は無視（start/end方式にフォールバック）
            pass
        elif m == -1:
            errors.append(RowError(row_number, "minutes_invalid: not an integer", row))
            return None, errors
        elif m <= 0:
            errors.append(RowError(row_number, "minutes_invalid: must be integer > 0", row))
            return None, errors
        else:
            # 有効なminutesが指定されている
            return NormalizedRow(date, process, operator, m, note), []
    
    # start/end方式の処理
    start = (row.get("start") or "").strip()
    end = (row.get("end") or "").strip()
    
    if not start or not end:
        # ここは validate_time_rules() が責務を持つ
        # build側で理由の異なるエラーを追加しないため、黙ってスキップする
        return None, []
    
    smin = _parse_hhmm_to_minutes(start)
    emin = _parse_hhmm_to_minutes(end)
    
    if smin is None:
        errors.append(RowError(row_number, "start_invalid: expected HH:MM", row))
        return None, errors
    
    if emin is None:
        errors.append(RowError(row_number, "end_invalid: expected HH:MM", row))
        return None, errors
    
    # 日跨ぎを許可（validate_time_rules()は順序チェックをしていない）
    # end < start の場合は日跨ぎとして扱う
    if emin < smin:
        # 日跨ぎ: (24時間 - start) + end
        diff = (24 * 60) - smin + emin
    else:
        # 通常: end - start
        diff = emin - smin
    
    # diffが0以下はエラー（同一時刻または逆転は許可しない）
    if diff <= 0:
        errors.append(RowError(row_number, "time_order_invalid: end must be after start", row))
        return None, errors
    
    return NormalizedRow(date, process, operator, diff, note), []



