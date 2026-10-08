"""Fetch-only probe round 2 (costs 3 API requests). Saves raw JSON; analysis is in the notebook.

Run from the repo root:  python src/ingestion/probe_round2.py
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
PROBE_DIR = ROOT / "data" / "raw" / "ceda" / "_probe"


def fetch_and_save(session: requests.Session, url: str, body: dict, tag: str) -> None:
    """POST once, save the raw response and the request body, print a one-line status."""
    resp = session.post(url, json=body, timeout=120)
    name = f"{tag}_{datetime.now():%Y%m%dT%H%M%S}_http{resp.status_code}"
    (PROBE_DIR / f"{name}.json").write_bytes(resp.content)  # untouched
    (PROBE_DIR / f"{name}.request.json").write_text(json.dumps(body, indent=2), encoding="utf-8")
    left = resp.headers.get("RateLimit-Remaining")
    print(f"{tag}: HTTP {resp.status_code}, {len(resp.content):,} bytes, requests left this hour: {left}")
    if resp.status_code != 200:
        print("  body:", resp.text[:500])


def main() -> None:
    load_dotenv(ROOT / ".env")
    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    base = settings["sources"]["ceda"]["base_url"].rstrip("/") + "/agmarknet"
    key = os.getenv("CEDA_API_KEY")
    if not key:
        raise SystemExit("CEDA_API_KEY is empty in .env")

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {key}", "Accept": "application/json"})
    today = date.today().isoformat()
    jaipur_onion = {"commodity_id": 23, "state_id": 8, "district_id": [110]}

    calls = [
        ("markets", {"commodity_id": 23, "state_id": 8, "district_id": 110, "indicator": "price"},
         "markets_c23_s8_d110"),
        ("prices", {**jaipur_onion, "from_date": "2018-01-01", "to_date": today},
         f"prices_c23_s8_d110_2018-01-01_{today}"),
        ("quantities", {**jaipur_onion, "from_date": "2024-01-01", "to_date": "2024-01-31"},
         "quantities_c23_s8_d110_2024-01-01_2024-01-31"),
    ]
    for endpoint, body, tag in calls:
        fetch_and_save(session, f"{base}/{endpoint}", body, tag)
        time.sleep(2)


if __name__ == "__main__":
    main()