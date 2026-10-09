"""CEDA Agri Market API client.

PLUMBING. Built in pieces:
  1.8a name -> ID lookup (this part)
  1.8b one safe request (throttling, retries)
  1.8c save raw response + checks
  1.8d full loop + manifest
"""
import difflib
import json
import time
import pandas as pd
from datetime import date
from pathlib import Path
import requests

from src.utils.config import ROOT  ,get_secret, load_settings
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

# ---------- 1.8b: one safe request ----------

def make_session() -> requests.Session:
    """HTTP session carrying the API key. The key is never logged."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {get_secret('CEDA_API_KEY')}",
        "Accept": "application/json",
    })
    return session


def seconds_until_reset(response: requests.Response) -> float:
    """Seconds to wait until the hourly quota resets.

    RateLimit-Reset's format is undocumented: a huge number is treated as a
    clock timestamp, a small one as seconds remaining. Falls back to 60 s.
    """
    try:
        value = float(response.headers.get("RateLimit-Reset"))
    except (TypeError, ValueError):
        return 60.0
    if value > 1_000_000_000:  # looks like a Unix timestamp
        value -= time.time()
    return max(value, 0) + 2  # 2 s safety margin


def ceda_request(session: requests.Session, method: str, path: str,
                 body: dict | None = None) -> requests.Response:
    """Send one request politely.

    - waits for the quota reset when RateLimit-Remaining hits 0
    - retries on 429, server errors (5xx) and network errors
    - stops immediately on other errors (a 4xx means our request is wrong)
    """
    cfg = load_settings()["sources"]["ceda"]
    url = f"{cfg['base_url']}{path}"

    for attempt in range(1, cfg["max_retries"] + 1):
        try:
            resp = session.request(method, url, json=body, timeout=cfg["timeout_seconds"])
        except requests.RequestException as err:
            wait = 2 ** attempt
            log.warning("%s %s failed (%s); retry %d in %ds", method, path, err, attempt, wait)
            time.sleep(wait)
            continue

        remaining = resp.headers.get("RateLimit-Remaining")
        log.info("%s %s -> HTTP %s | quota left %s | reset %s", method, path,
                 resp.status_code, remaining, resp.headers.get("RateLimit-Reset"))

        if resp.status_code == 429:
            wait = seconds_until_reset(resp)
            log.warning("Rate limit hit; sleeping %.0f s", wait)
            time.sleep(wait)
            continue
        if resp.status_code >= 500:
            wait = 2 ** attempt
            log.warning("Server error; retry %d in %ds", attempt, wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()  # any other error: stop, don't waste quota

        if remaining is not None and int(remaining) == 0:
            wait = seconds_until_reset(resp)
            log.info("Quota used up; sleeping %.0f s before continuing", wait)
            time.sleep(wait)
        return resp

    raise RuntimeError(f"{method} {path} failed after {cfg['max_retries']} attempts")

# ---------- 1.8c: response checks ----------

def check_response(payload: dict, start_date: str, endpoint: str) -> list[str]:
    """Return a list of problems. Empty list = response is OK."""
    output = payload.get("output")
    if output is None:
        return ["missing 'output' wrapper"]

    problems = []
    if output.get("type") != "success":
        problems.append(f"type is {output.get('type')!r}, expected 'success'")
    if output.get("message") != "Data exists":
        problems.append(f"message is {output.get('message')!r}, expected 'Data exists'")

    data = output.get("data")
    if not data:
        problems.append("data is empty or missing")
        return problems  # no rows -> nothing more to check

    df = pd.DataFrame(data)

    # Check 4 (you write): dates
    if "date"  not in df.columns:
        problems.append("no date column ")
    else:
        dates = df["date"].str[:10]
        n_missing = dates.isnull().sum()
        if n_missing > 0:
            problems.append(f"{n_missing} rows have no date")
        dates = dates.dropna()
        today = date.today().isoformat()
        if not dates.empty and dates.min() < start_date:
            problems.append(f"earliest date {dates.min()} is before start_date {start_date}")
        if not dates.empty and dates.max() > today:
            problems.append(f"latest date {dates.max()} is after today {today}")
    # Check 5 (you write): modal price, prices endpoint only
    if endpoint == "prices":
        if 'modal_price' not in df.columns:
            problems.append('no modal price found')
        else:
            if df['modal_price'].isnull().any():
                problems.append(f"the modal price column contains {df['modal_price'].isnull().sum()} null values")
        
    return problems
