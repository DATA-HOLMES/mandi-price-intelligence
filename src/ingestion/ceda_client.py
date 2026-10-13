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
from datetime import date, datetime
from pathlib import Path
import requests

from src.utils.config import ROOT  ,get_secret, load_settings
from src.utils.logger import get_logger

log = get_logger("ceda_client")
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

# ---------- 1.8c: save raw responses ----------

RAW_DIR: Path = ROOT / "data" / "raw" / "ceda"


def raw_name(endpoint: str, commodity_id: int, state_id: int, start: str, end: str) -> str:
    """File name stem, same pattern as the probes, e.g. prices_c23_s8_dALL_2018-01-01_2026-10-10."""
    return f"{endpoint}_c{commodity_id}_s{state_id}_dALL_{start}_{end}"


def save_raw(resp: requests.Response, name: str, body: dict | None = None) -> Path:
    """Save the response bytes untouched, plus a .request.json describing the call.

    The Authorization header (API key) is never written to disk.
    """
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    stem = f"{name}_{stamp}_http{resp.status_code}"
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    data_path = RAW_DIR / f"{stem}.json"
    data_path.write_bytes(resp.content)  # exactly as received

    request_info = {
        "url": resp.url,
        "method": resp.request.method,
        "body": body,
        "requested_at": stamp,
        "http_status": resp.status_code,
        "ratelimit_remaining": resp.headers.get("RateLimit-Remaining"),
        "ratelimit_reset": resp.headers.get("RateLimit-Reset"),
    }
    (RAW_DIR / f"{stem}.request.json").write_text(
        json.dumps(request_info, indent=2), encoding="utf-8"
    )
    log.info("Saved %s (%d bytes)", data_path.name, len(resp.content))
    return data_path

# ---------- 1.8d: full pull + manifest ----------

MANIFEST_PATH: Path = RAW_DIR / "manifest.csv"
ENDPOINTS = ["prices", "quantities"]


def get_lookups(session: requests.Session | None) -> tuple[list[dict], list[dict]]:
    """Commodities + geographies lists.

    Live (2 requests, saved untouched) if a session is given; otherwise the
    newest saved copies (free, used for dry runs).
    """
    if session is None:
        def load(pattern: str) -> list[dict]:
            newest = max(RAW_DIR.rglob(pattern), key=lambda p: p.stat().st_mtime)
            return json.loads(newest.read_text(encoding="utf-8"))["output"]["data"]
        return load("commodities_*_http200.json"), load("geographies_*_http200.json")

    out = []
    for endpoint in ["commodities", "geographies"]:
        resp = ceda_request(session, "GET", f"/agmarknet/{endpoint}")
        save_raw(resp, endpoint)
        out.append(resp.json()["output"]["data"])
    return out[0], out[1]


def load_manifest() -> pd.DataFrame:
    """One row per attempted request. Empty table if no pull has run yet."""
    if MANIFEST_PATH.exists():
        return pd.read_csv(MANIFEST_PATH, dtype=str)
    return pd.DataFrame(columns=["key", "status"])


def append_manifest(row: dict) -> None:
    """Add one row to manifest.csv (written straight after every request)."""
    pd.DataFrame([row]).to_csv(
        MANIFEST_PATH, mode="a", index=False, header=not MANIFEST_PATH.exists()
    )


def pull_one(session: requests.Session, endpoint: str, key: str, name: str,
             body: dict, start: str, state: str, commodity: str) -> None:
    """Send one request, save it untouched, check it, record it in the manifest."""
    row = {"key": key, "state": state, "commodity": commodity, "endpoint": endpoint,
           "fetched_at": datetime.now().isoformat(timespec="seconds")}
    try:
        resp = ceda_request(session, "POST", f"/agmarknet/{endpoint}", body)
        path = save_raw(resp, name, body)
        payload = resp.json()
    except Exception as err:  # record any failure and keep going
        append_manifest({**row, "file": "", "rows": "", "min_date": "", "max_date": "",
                         "problems": str(err), "status": "failed"})
        log.error("FAILED %s: %s", key, err)
        return

    problems = check_response(payload, start, endpoint)
    data = payload.get("output", {}).get("data") or []
    dates = sorted(r["date"][:10] for r in data if r.get("date"))
    if data and len(data) % 1000 == 0:
        problems.append(f"row count {len(data)} is a round number: possible truncation")

    append_manifest({**row, "file": path.name, "rows": len(data),
                     "min_date": dates[0] if dates else "",
                     "max_date": dates[-1] if dates else "",
                     "problems": "; ".join(problems),
                     "status": "check" if problems else "ok"})
    log.info("%s: %d rows, %s to %s, %s", key, len(data),
             dates[0] if dates else "-", dates[-1] if dates else "-",
             "CHECK: " + "; ".join(problems) if problems else "ok")


def run_pull(dry_run: bool = False) -> None:
    """Pull prices + quantities for every state x commodity in settings.yaml.

    Re-running is safe: requests already logged 'ok' or 'check' are skipped;
    only 'failed' ones are tried again.
    """
    settings = load_settings()
    start, end = settings["scope"]["start_date"], date.today().isoformat()
    session = None if dry_run else make_session()

    commodities, geographies = get_lookups(session)
    ids = resolve_ids(settings, commodities, geographies)
    if not dry_run:
        save_ids_snapshot(ids)

    manifest = load_manifest()
    done = set(manifest.loc[manifest["status"].isin(["ok", "check"]), "key"])

    for state, state_id in ids["states"].items():
        districts = sorted({g["census_district_id"] for g in geographies
                            if g["census_state_id"] == state_id})
        for commodity, commodity_id in ids["commodities"].items():
            for endpoint in ENDPOINTS:
                key = f"{endpoint}_c{commodity_id}_s{state_id}"
                if key in done:
                    log.info("Skip %s (already done)", key)
                    continue
                body = {"commodity_id": commodity_id, "state_id": state_id,
                        "district_id": districts, "from_date": start, "to_date": end}
                if dry_run:
                    log.info("PLAN %s | %s | %s | %d districts", key, state,
                             commodity, len(districts))
                    continue
                pull_one(session, endpoint, key, raw_name(endpoint, commodity_id,
                         state_id, start, end), body, start, state, commodity)

    log.info("Finished. Manifest: %s", MANIFEST_PATH)


if __name__ == "__main__":
    import sys
    run_pull(dry_run="--dry-run" in sys.argv)