"""One /prices call: Jaipur onion, January 2024. Costs 1 API request.

Answers: does district_id take Census ids, is market_id optional, does the
response carry variety/grade, and are there several rows per date x market?
Run from the repo root:  python src/ingestion/probe_prices.py
Temporary helper: its logic moves into ceda_client.py, then this file is deleted.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
PROBE_DIR = ROOT / "data" / "raw" / "ceda" / "_probe"
BODY = {
    "commodity_id": 23,      # Onion
    "state_id": 8,           # Rajasthan (Census 2011)
    "district_id": [110],    # Jaipur (Census 2011)
    "from_date": "2024-01-01",
    "to_date": "2024-01-31",
}


def main() -> None:
    load_dotenv(ROOT / ".env")
    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))
    base_url = settings["sources"]["ceda"]["base_url"].rstrip("/")
    key = os.getenv("CEDA_API_KEY")
    if not key:
        raise SystemExit("CEDA_API_KEY is empty in .env")

    resp = requests.post(
        f"{base_url}/agmarknet/prices",
        json=BODY,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        timeout=60,
    )
    print(f"POST /agmarknet/prices -> HTTP {resp.status_code}, {len(resp.content):,} bytes")
    print("  rate-limit:", {k: v for k, v in resp.headers.items() if k.lower().startswith("ratelimit")})

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    name = f"prices_c23_s8_d110_2024-01-01_2024-01-31_{stamp}_http{resp.status_code}"
    (PROBE_DIR / f"{name}.json").write_bytes(resp.content)                        # untouched
    (PROBE_DIR / f"{name}.request.json").write_text(json.dumps(BODY, indent=2), encoding="utf-8")
    print(f"  saved raw -> data/raw/ceda/_probe/{name}.json")

    if resp.status_code != 200:
        print("  body:", resp.text[:800])
        return

    out = resp.json().get("output", {})
    rows = out.get("data") or []
    print(f"  type={out.get('type')}  message={out.get('message')}  rows={len(rows)}")
    if not rows:
        return

    df = pd.DataFrame(rows)
    print(f"\ncolumns: {list(df.columns)}")
    print(df.head(5).to_string(index=False))

    for col in ("min_price", "max_price", "modal_price"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"\ndistinct markets: {df['market_id'].nunique()}  -> {sorted(df['market_id'].unique().tolist())}")
    print(f"dates: {df['date'].min()} to {df['date'].max()}, {df['date'].nunique()} distinct")

    # Key test: one row per date x market, or several?
    key_cols = ["date", "market_id"] + [c for c in ("variety", "grade") if c in df.columns]
    sizes = df.groupby(key_cols).size()
    multi = sizes[sizes > 1]
    print(f"\ngroups on {key_cols}: {len(sizes)}; groups with >1 row: {len(multi)}")
    if len(multi):
        differing = (
            df.groupby(key_cols)["modal_price"].nunique().loc[multi.index].gt(1).sum()
        )
        print(f"  of those, groups with DIFFERENT modal prices: {differing}")
        first = multi.index[0]
        mask = (df[key_cols] == pd.Series(first, index=key_cols)).all(axis=1)
        print("  example group:")
        print(df[mask].to_string(index=False))

    # Sanity: plausible Rs/kg and internal consistency
    kg = df["modal_price"] / 100
    print(f"\nmodal Rs/kg: min {kg.min():.1f}, median {kg.median():.1f}, max {kg.max():.1f}")
    print(f"min > max rows: {(df['min_price'] > df['max_price']).sum()}")
    print(f"modal outside [min, max] rows: "
          f"{((df['modal_price'] < df['min_price']) | (df['modal_price'] > df['max_price'])).sum()}")


if __name__ == "__main__":
    main()