"""CEDA Agri Market API client.

PLUMBING. Built in pieces:
  1.8a name -> ID lookup (this part)
  1.8b one safe request (throttling, retries)
  1.8c save raw response + checks
  1.8d full loop + manifest
"""
import difflib
import json
from datetime import date
from pathlib import Path

from src.utils.config import ROOT
from src.utils.logger import get_logger

log = get_logger(__name__)
IDS_PATH: Path = ROOT / "data" / "reference" / "ceda_ids.json"


def find_id(rows: list[dict], name_field: str, id_field: str, name: str) -> int:
    """Return the single ID whose name matches `name` exactly.

    Raises ValueError on zero or several distinct IDs. Suggests close
    names in the error, but never accepts them automatically.
    """
    ids = {r[id_field] for r in rows if r[name_field] == name}
    if len(ids) == 1:
        return ids.pop()
    if not ids:
        close = difflib.get_close_matches(name, {r[name_field] for r in rows}, n=3)
        raise ValueError(f"No exact match for {name!r}. Close names: {close}")
    raise ValueError(f"{name!r} matches several IDs: {sorted(ids)}")


def resolve_ids(settings: dict, commodities: list[dict], geographies: list[dict]) -> dict:
    """Turn the names in settings['scope'] into CEDA / Census 2011 IDs."""
    scope = settings["scope"]
    states = [scope["home_state"], *scope["supply_states"]]

    commodity_ids = {
        c: find_id(commodities, "commodity_name", "commodity_id", c)
        for c in scope["commodities"]
    }
    state_ids = {
        s: find_id(geographies, "census_state_name", "census_state_id", s)
        for s in states
    }
    # Look up the home district only inside the home state
    home_state_rows = [
        g for g in geographies if g["census_state_id"] == state_ids[scope["home_state"]]
    ]
    district_id = find_id(
        home_state_rows, "census_district_name", "census_district_id", scope["home_district"]
    )
    return {
        "commodities": commodity_ids,
        "states": state_ids,
        "home_district": {scope["home_district"]: district_id},
    }


def save_ids_snapshot(ids: dict) -> Path:
    """Save the resolved IDs, with today's date, to data/reference/ceda_ids.json."""
    IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"resolved_on": date.today().isoformat(), **ids}
    IDS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Saved ID snapshot to %s", IDS_PATH)
    return IDS_PATH