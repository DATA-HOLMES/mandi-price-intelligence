"""Load project settings (config/settings.yaml) and secrets (.env).

PLUMBING: no analysis here. Every script imports from this module so that
paths and credentials are never hard-coded.
"""
from functools import lru_cache
from pathlib import Path
import os

import yaml
from dotenv import load_dotenv

# This file is src/utils/config.py -> parents[2] is the project root,
# no matter which folder the code is run from.
ROOT: Path = Path(__file__).resolve().parents[2]
SETTINGS_PATH: Path = ROOT / "config" / "settings.yaml"


@lru_cache(maxsize=1)
def load_settings() -> dict:
    """Read settings.yaml once and return it as a dict (cached after first call)."""
    with SETTINGS_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_secret(name: str) -> str:
    """Return a secret from .env. Raise an error if it is missing or empty."""
    load_dotenv(ROOT / ".env")
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is missing or empty in .env")
    return value