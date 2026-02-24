# worklog_tool

工場の「作業ログ」をCSVで入力し、検証→整形→集計→レポート出力（CSV + HTML）するローカル完結ツールです。  
Excelなし前提（出力はCSV/HTML）。

## Requirements
- Windows + PowerShell
- Python 3.11+
- （任意）Git

## Setup
```powershell
cd C:\work\worklog_tool
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
```

## Input
- UTF-8 の CSV（例: `data/raw/sample_worklog.csv`）
- 1行 = 1作業
- 必須列: `date, process, operator`
- 時間は2方式:
  - A) `start,end`（HH:MM） → minutes を計算
  - B) `minutes`（整数） → それを使用
- 任意: `note`

例:
```csv
date,start,end,process,operator,minutes,note
2026-02-13,09:00,09:40,ミキサー準備,A,,洗浄
2026-02-13,,,,ミキサー準備,A,25,minutesだけでも記録可
```

## Commands

### 1) validate（入力検証）
```powershell
python -m src.tool.cli validate
```
- 検証エラー: `reports/errors.csv` に「行番号 + 理由 + 生データ」を出力
- 実行ログ: `logs/run.log`

### 2) build（整形→集計→レポート出力）
```powershell
python -m src.tool.cli build
```

出力（MVP）:
- `reports/summary_daily.csv`
- `reports/summary_process.csv`
- `reports/report.html`
- `reports/errors.csv`
- `logs/run.log`

※ エラー行があっても落とさず、正常行だけでサマリを作ります。

## Tests
```powershell
pytest -q
```

## Troubleshooting

### PowerShellで `type` すると日本語が文字化けする
UTF-8として読む:
```powershell
Get-Content .\data\raw\sample_worklog.csv -Encoding utf8
```

### pytestで `No module named 'src'` が出る
`tests/conftest.py` がプロジェクトルートを `sys.path` に追加します（本プロジェクトは対応済み）。

## Notes
- Webアクセス不要（ローカル完結）
- 仕様はMVPから順次拡張します