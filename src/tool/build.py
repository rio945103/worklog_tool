# src/tool/build.py
from __future__ import annotations

import csv
import logging
from pathlib import Path

from .normalize import NormalizedRow, normalize_row
from .validate import RowError, read_csv_utf8, validate_required_columns, validate_time_rules, write_errors_csv

logger = logging.getLogger("worklog_tool")


def _row_has_error(row_number: int, errors: list[RowError]) -> bool:
    return any(e.row_number == row_number for e in errors)


def run_build(input_csv: Path, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)

    errors_csv = out_dir / "errors.csv"
    summary_daily_csv = out_dir / "summary_daily.csv"
    summary_process_csv = out_dir / "summary_process.csv"
    report_html = out_dir / "report.html"

    logger.info(f"build: start input={input_csv} out_dir={out_dir}")

    _, rows = read_csv_utf8(input_csv)

    # 既存validate（必須列＋時間ルール）
    errors: list[RowError] = []
    errors.extend(validate_required_columns(rows))
    errors.extend(validate_time_rules(rows))

    normalized: list[NormalizedRow] = []

    # 正規化処理（normalize_rowで統一）
    for i, row in enumerate(rows, start=2):
        if _row_has_error(i, errors):
            continue

        norm_row, norm_errors = normalize_row(i, row)
        if norm_errors:
            errors.extend(norm_errors)
            continue
        
        if norm_row is not None:
            normalized.append(norm_row)

    # errors は常に出す（空でもOK）
    write_errors_csv(errors_csv, errors)

    # 有効行が0でも、空のサマリを出す（落とさない）
    _export_summary_daily(summary_daily_csv, normalized)
    _export_summary_process(summary_process_csv, normalized)
    _export_html(report_html, normalized, errors)

    logger.info(
        f"build: rows={len(rows)} valid={len(normalized)} errors={len(errors)} "
        f"outputs={summary_daily_csv},{summary_process_csv},{report_html}"
    )
    logger.info("build: finished")

    # エラーがあっても出力は作る。終了コードは 0/2 で区別。
    if errors:
        print(f"BUILD DONE (with errors): errors={len(errors)} -> {errors_csv}")
        return 2

    print(f"BUILD DONE: reports written to {out_dir}")
    return 0


def _export_summary_daily(path: Path, items: list[NormalizedRow]) -> None:
    # 日別: 総minutes, 作業回数, 工程別内訳（process=minutesを;区切り）
    daily: dict[str, dict[str, int]] = {}
    daily_count: dict[str, int] = {}
    daily_process: dict[str, dict[str, int]] = {}

    for r in items:
        daily.setdefault(r.date, {"total_minutes": 0})
        daily[r.date]["total_minutes"] += r.minutes

        daily_count[r.date] = daily_count.get(r.date, 0) + 1

        pm = daily_process.setdefault(r.date, {})
        pm[r.process] = pm.get(r.process, 0) + r.minutes

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "total_minutes", "work_count", "process_breakdown"])
        for date in sorted(daily.keys()):
            breakdown = ";".join([f"{p}={m}" for p, m in sorted(daily_process[date].items())])
            w.writerow([date, daily[date]["total_minutes"], daily_count[date], breakdown])


def _export_summary_process(path: Path, items: list[NormalizedRow]) -> None:
    # 工程別: 回数, 合計, 平均, 最大
    agg: dict[str, dict[str, int]] = {}
    for r in items:
        a = agg.setdefault(r.process, {"count": 0, "sum": 0, "max": 0})
        a["count"] += 1
        a["sum"] += r.minutes
        a["max"] = max(a["max"], r.minutes)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["process", "count", "sum_minutes", "avg_minutes", "max_minutes"])
        for process in sorted(agg.keys()):
            a = agg[process]
            avg = round(a["sum"] / a["count"], 2) if a["count"] else 0
            w.writerow([process, a["count"], a["sum"], avg, a["max"]])


def _export_html(path: Path, items: list[NormalizedRow], errors: list[RowError]) -> None:
    # daily
    daily_totals: dict[str, int] = {}
    daily_counts: dict[str, int] = {}
    for r in items:
        daily_totals[r.date] = daily_totals.get(r.date, 0) + r.minutes
        daily_counts[r.date] = daily_counts.get(r.date, 0) + 1

    # process
    proc_totals: dict[str, int] = {}
    proc_counts: dict[str, int] = {}
    for r in items:
        proc_totals[r.process] = proc_totals.get(r.process, 0) + r.minutes
        proc_counts[r.process] = proc_counts.get(r.process, 0) + 1

    html: list[str] = []
    html.append("<!doctype html><html><head><meta charset='utf-8'>")
    html.append("<title>Worklog Report</title></head><body>")
    html.append("<h1>Worklog Report</h1>")
    html.append(f"<p>valid rows: {len(items)}</p>")

    # errors summary
    html.append("<h2>Errors</h2>")
    html.append(f"<p>errors: {len(errors)}</p>")
    if errors:
        html.append("<table border='1' cellpadding='4' cellspacing='0'>")
        html.append("<tr><th>row_number</th><th>reason</th></tr>")
        for e in errors[:10]:
            html.append(f"<tr><td>{e.row_number}</td><td>{e.reason}</td></tr>")
        html.append("</table>")
        if len(errors) > 10:
            html.append("<p>(showing first 10)</p>")

    html.append("<h2>Daily Summary</h2>")
    html.append("<table border='1' cellpadding='4' cellspacing='0'>")
    html.append("<tr><th>date</th><th>total_minutes</th><th>work_count</th></tr>")
    for d in sorted(daily_totals.keys()):
        html.append(f"<tr><td>{d}</td><td>{daily_totals[d]}</td><td>{daily_counts[d]}</td></tr>")
    html.append("</table>")

    html.append("<h2>Process Summary</h2>")
    html.append("<table border='1' cellpadding='4' cellspacing='0'>")
    html.append("<tr><th>process</th><th>count</th><th>sum_minutes</th></tr>")
    for p in sorted(proc_totals.keys()):
        html.append(f"<tr><td>{p}</td><td>{proc_counts[p]}</td><td>{proc_totals[p]}</td></tr>")
    html.append("</table>")

    html.append("</body></html>")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(html), encoding="utf-8")
