# src/tool/logging_utils.py
from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_path: Path = Path("logs/run.log")) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("worklog_tool")
    logger.setLevel(logging.INFO)

    # 二重登録防止（再実行やテストでハンドラが増えないようにする）
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger
