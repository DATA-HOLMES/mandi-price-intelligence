"""Standard logging setup: console + logs/<name>.log.

PLUMBING: every script does `log = get_logger(__name__)` and uses
log.info / log.warning / log.error instead of print().
Never log secrets (API key, DB password).
"""
import logging
from pathlib import Path

from src.utils.config import ROOT

LOG_DIR: Path = ROOT / "logs"
FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger writing to the console and logs/<short name>.log.

    Safe to call repeatedly (e.g. re-running a notebook cell):
    handlers are attached only the first time.
    """
    logger = logging.getLogger(name)
    if logger.handlers:  # already set up -> don't add duplicate handlers
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    LOG_DIR.mkdir(exist_ok=True)
    short_name = name.split(".")[-1]  # "src.ingestion.ceda_client" -> "ceda_client"
    file_handler = logging.FileHandler(LOG_DIR / f"{short_name}.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False  # stop messages printing twice via the root logger
    return logger