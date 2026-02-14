# tests/test_build_minutes.py
from pathlib import Path

from src.tool.build import run_build


def test_build_uses_minutes_and_writes_daily_summary(tmp_path: Path):
    # 入力CSVを作る（minutes方式1行）
    input_csv = tmp_path / "in.csv"
    input_csv.write_text(
        "\n".join(
            [
                "date,start,end,process,operator,minutes,note",
                "2026-02-13,,,ミキサー準備,A,25,test",
            ]
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "reports"

    code = run_build(input_csv, out_dir)

    # エラー無しのはず
    assert code == 0

    daily = (out_dir / "summary_daily.csv").read_text(encoding="utf-8")
    assert "2026-02-13,25,1" in daily
