# tests/test_build_start_end.py
from pathlib import Path

from src.tool.build import run_build


def test_build_calculates_minutes_from_start_end(tmp_path: Path):
    input_csv = tmp_path / "in.csv"
    input_csv.write_text(
        "\n".join(
            [
                "date,start,end,process,operator,minutes,note",
                "2026-02-13,09:00,09:40,ミキサー準備,A,,test",
            ]
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "reports"

    code = run_build(input_csv, out_dir)

    assert code == 0

    daily = (out_dir / "summary_daily.csv").read_text(encoding="utf-8")
    assert "2026-02-13,40,1" in daily
