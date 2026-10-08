"""Fetch-only probe round 3 (2 API requests): Rajasthan onion, all districts, 2018 -> today.

Tests whether a whole-state request returns everything. Analysis is in the notebook.
Run from the repo root:  python src/ingestion/probe_round3.py
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
    """POST once, save raw response + request body, print status, size and time taken."""
    t0 = time.perf_counter()
    resp = session.post(url, json=body, timeout=300)
    secs = time.perf_counter() - t0
    name = f"{tag}_{datetime.now():%Y%m%dT%H%M%S}_http{resp.status_code}"
    (PROBE_DIR / f"{name}.json").write_bytes(resp.content)  # untouched
    (PROBE_DIR / f"{name}.request.json").write_text(json.dumps(body, indent=2), encoding="utf-8")
    left = resp.headers.get("RateLimit-Remaining")
    print(f"{tag}: HTTP {resp.status_code}, {len(resp.content):,} bytes, {secs:.1f}s, requests left: {left}")
    if resp.status_code != 200:
        print("  body:", resp.text[:500])


def main() -> None:
    load_dotenv(ROOT / ".env")
    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    base = settings["sources"]["ceda"]["base_url"].rstrip("/") + "/agmarknet"
    key = os.getenv("CEDA_API_KEY")
    if not key:
        raise SystemExit("CEDA_API_KEY is empty in .env")

    geo_path = sorted(PROBE_DIR.glob("geographies_*_http200.json"))[-1]
    geo = json.loads(geo_path.read_text(encoding="utf-8"))["output"]["data"]
    raj = sorted(r["census_district_id"] for r in geo if r["census_state_id"] == 8)
    print(f"Rajasthan districts in request: {len(raj)}")

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {key}", "Accept": "application/json"})
    today = date.today().isoformat()
    body = {"commodity_id": 23, "state_id": 8, "district_id": raj,
            "from_date": "2018-01-01", "to_date": today}

    for endpoint in ("prices", "quantities"):
        fetch_and_save(session, f"{base}/{endpoint}", body, f"{endpoint}_c23_s8_dALL_2018-01-01_{today}")
        time.sleep(2)


if __name__ == "__main__":
    main()