"""Read the saved CEDA probe responses (no API calls) and print the ids we need.

Run from the repo root:  python src/ingestion/parse_probe.py
Temporary helper: its logic moves into ceda_client.py, then this file is deleted.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PROBE_DIR = ROOT / "data" / "raw" / "ceda" / "_probe"


def load_latest(prefix: str) -> dict:
    """Return the 'output' block of the newest saved probe file for an endpoint."""
    path = sorted(PROBE_DIR.glob(f"{prefix}_*_http200.json"))[-1]
    print(f"\nreading {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))["output"]


def main() -> None:
    scope = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))["scope"]
    commodities = [c.lower() for c in scope["commodities"]]
    states = [scope["home_state"].lower()] + [s.lower() for s in scope["supply_states"]]

    com = load_latest("commodities")
    print(f"  type={com['type']}  message={com['message']}  rows={len(com['data'])}")
    print("  substring matches (review by eye):")
    for c in com["data"]:
        if any(t in c["commodity_name"].lower() for t in commodities):
            print(f"    commodity_id={c['commodity_id']:>5}  {c['commodity_name']}")

    geo = load_latest("geographies")
    rows = geo["data"]
    print(f"  type={geo['type']}  message={geo['message']}  rows={len(rows)}")
    print(f"  distinct states/UTs: {len({r['census_state_id'] for r in rows})}")
    print(f"  distinct districts:  {len({r['census_district_id'] for r in rows})}")

    per_state = Counter(
        (r["census_state_id"], r["census_state_name"])
        for r in rows
        if r["census_state_name"].strip().lower() in states
    )
    print("  our states:")
    for (sid, name), n in sorted(per_state.items()):
        print(f"    census_state_id={sid:>3}  {name}: {n} districts")
    missing = set(states) - {name.strip().lower() for (_, name) in per_state}
    print(f"  state names not matched: {sorted(missing) or 'none'}")

    print("  districts containing 'jaipur':")
    for r in rows:
        if "jaipur" in r["census_district_name"].lower():
            print(f"    {r}")


if __name__ == "__main__":
    main()