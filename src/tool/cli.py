# src/tool/cli.py
import argparse
from pathlib import Path

from .validate import run_validate

from .build import run_build

from .logging_utils import setup_logging

def main(argv=None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(prog="worklog-tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("hello", help="sanity check")

    p_val = sub.add_parser("validate", help="validate input CSV and write reports/errors.csv")
    p_val.add_argument("--input", default="data/raw/sample_worklog.csv")

    p_build = sub.add_parser("build", help="transform/aggregate and write reports (CSV+HTML)")
    p_build.add_argument("--input", default="data/raw/sample_worklog.csv")
    p_build.add_argument("--out", default="reports")

    args = parser.parse_args(argv)

    if args.cmd == "hello":
        print("hello worklog_tool")
        return 0

    if args.cmd == "validate":
        input_csv = Path(args.input)
        errors_csv = Path("reports/errors.csv")
        return run_validate(input_csv, errors_csv)

    if args.cmd == "build":
        input_csv = Path(args.input)
        out_dir = Path(args.out)
        return run_build(input_csv, out_dir)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
