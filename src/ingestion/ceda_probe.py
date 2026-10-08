"""Probe the CEDA API lookup endpoints before writing the full client.

Answers four questions:
  1. Does Bearer auth with our key work?
  2. Does /geographies need a commodity_id (the docs are inconsistent)?
  3. What ids do Onion, Tomato, Potato and our five states have?
  4. Does the API send any rate-limit headers?

Raw responses are saved untouched to data/raw/ceda/_probe/.
Run from the repo root:  python src/ingestion/ceda_probe.py
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
# Temporary: config.py (next sub-step) will own paths and timeouts.
PROBE_DIR = ROOT / "data" / "raw" / "ceda" / "_probe"
TIMEOUT_S = 60


def load_settings() -> dict:
    """Read config/settings.yaml."""
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


def fetch(session: requests.Session, url: str, name: str) -> requests.Response:
    """GET a URL, report status, size and rate-limit headers, save the raw body."""
    resp = session.get(url, timeout=TIMEOUT_S)
    print(f"\nGET {url} -> HTTP {resp.status_code}, {len(resp.content):,} bytes")
    rate_headers = {
        k: v for k, v in resp.headers.items()
        if "rate" in k.lower() or "retry" in k.lower() or "limit" in k.lower()
    }
    print(f"  rate-limit headers: {rate_headers or 'none'}")

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out = PROBE_DIR / f"{name}_{stamp}_http{resp.status_code}.json"
    out.write_bytes(resp.content)  # untouched
    print(f"  saved raw -> {out.relative_to(ROOT)}")

    if resp.status_code != 200:
        print(f"  body (first 500 chars): {resp.text[:500]}")
    return resp


def main() -> None:
    load_dotenv(ROOT / ".env")
    settings = load_settings()
    base_url = settings["sources"]["ceda"]["base_url"].rstrip("/")
    key = os.getenv("CEDA_API_KEY")
    if not key:
        raise SystemExit("CEDA_API_KEY is empty in .env")

    scope = settings["scope"]
    target_commodities = [c.lower() for c in scope["commodities"]]
    target_states = [scope["home_state"].lower()] + [s.lower() for s in scope["supply_states"]]

    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {key}", "Accept": "application/json"})

    # 1. Commodities
    resp = fetch(session, f"{base_url}/agmarknet/commodities", "commodities")
    if resp.status_code == 200:
        items = resp.json().get("commodities", [])
        print(f"  total commodities: {len(items)}")
        print("  matches for our commodities (substring match, review by eye):")
        for c in items:
            if any(t in str(c.get("name", "")).lower() for t in target_commodities):
                print(f"    id={c.get('id')!s:>5}  name={c.get('name')}")

    time.sleep(1.0)  # polite delay; real limit unknown

    # 2. Geographies (docs list no params; test that claim)
    resp = fetch(session, f"{base_url}/agmarknet/geographies", "geographies")
    if resp.status_code == 200:
        states = resp.json().get("geographies", [])
        print(f"  total states/UTs: {len(states)}")
        for s in states:
            if str(s.get("state_name", "")).lower() in target_states:
                districts = s.get("districts", [])
                print(f"    state_id={s.get('state_id')!s:>3}  {s.get('state_name')}: {len(districts)} districts")
                for d in districts:
                    if "jaipur" in str(d.get("district_name", "")).lower():
                        print(f"      -> district_id={d.get('district_id')}  {d.get('district_name')}")


if __name__ == "__main__":
    main()