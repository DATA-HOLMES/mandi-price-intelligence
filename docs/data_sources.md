# Data Sources

## 1. CEDA Agri Market Data (primary historical source)

### Provider and links
- Portal: https://agmarknet.ceda.ashoka.edu.in/
- README: https://agmarknet.ceda.ashoka.edu.in/README.html
- API base: https://api.ceda.ashoka.edu.in/v1
- Docs: https://api.ceda.ashoka.edu.in/documentation/
- Terms: https://ceda.ashoka.edu.in/api-terms-conditions/
- Original source: Directorate of Marketing & Inspection (DMI), Ministry of Agriculture and Farmers Welfare
- Accessed: 2026-10-04
### Licence and citation
- Free for non-commercial use.
- Required citation: "CEDA Agri Market Data (CEDA-AMD), 2000-2023". Centre for Economic Data & Analysis, Ashoka University, https://ceda.ashoka.edu.in/agmarknet
- Every visualization needs the CEDA logo in the bottom right plus a text credit to the Centre for Economic Data & Analysis, Ashoka University.
- No endorsement may be implied, and there's no warranty of accuracy.
### Access
- Free API key via email OTP, sent as the header `Authorization: Bearer <key>`.
- The key lives in `.env` and is never committed.
### Endpoints
  | Method | Endpoint | Purpose | Key inputs |
  |---|---|---|---|
  | GET | `/agmarknet/commodities` | Commodity id ↔ name lookup | none |
  | GET | `/agmarknet/geographies` | Census state and district lookup | none |
  | POST | `/agmarknet/markets` | Markets in a district | `commodity_id`, `state_id`, `district_id`, `indicator` |
  | POST | `/agmarknet/prices` | Daily min, max, modal price (₹/quintal) | `commodity_id`, `state_id`, `district_id` list, optional `market_id` list, `from_date`, `to_date` |
  | POST | `/agmarknet/quantities` | Daily arrivals (tonnes) | same as prices |
### Response format
- Real responses are wrapped as `{"output": {"type", "message", "data": [...]}}`.
- Field names differ from the Swagger examples (e.g. `commodity_id` and `commodity_name`, not `id` and `name`).
- `/geographies` needs no `commodity_id`, despite the docs.
- Dates come as `YYYY-MM-DDT00:00:00.000Z`; keep the date part only, with no timezone conversion.
- What: a successful response has `output.type = "success"` and `output.message = "Data exists"` (exact, lowercase "success").
  - Evidence: saved probe `prices_c23_s8_dALL_2018-01-01_2026-10-04_..._http200.json` (Rajasthan onion prices, 55,368 rows), checked 2026-10-10.
  - So what: HTTP 200 alone is not trusted. `check_response` in `ceda_client.py` also checks type, message, non-empty data, dates and modal price before a response is accepted.
  - Status: confirmed for a successful response. The type/message CEDA returns when no data exists is not yet seen; record it if it appears in the full pull (1.9).
### Identifiers
- Census 2011 coding: 36 states/UTs, 640 districts, 453 commodities.
- Onion 23, Potato 24, Tomato 78 (excluded: Sweet Potato 152, Onion Green 358).
- Rajasthan 8, Uttar Pradesh 9, Madhya Pradesh 23, Gujarat 24, Maharashtra 27.
- Jaipur district 110.
- Request `state_id` and `district_id` are Census IDs.
- `market_id` is optional; leaving it out returns all markets in the district.
### Units and grain
- Prices in ₹/quintal; arrivals in tonnes (README, confirmed by a sanity check: median ₹20/kg for Jaipur onion in January 2024).
- The API returns no variety or grade. The README says the underlying data is unique per variety and grade, so the API collapses varieties; the rule is undocumented.
- One row per date × market × commodity, with rare exceptions: 3 of 55,368 Rajasthan onion price rows share a date and market with different prices (likely unlabeled varieties). See `data_quality_report.md`.
### Rate limit
- Limit: 40 requests per hour, fixed window starting at the first call.
- Headers: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`. HTTP 429 when exceeded.
- `RateLimit-Reset` = seconds until the window resets (not a clock time).
  - Evidence: first call of the hour on 2026-10-09 returned Remaining = 39, Reset = 3600 (exactly 1 hour).
  - So what: when Remaining reaches 0, or a 429 arrives, `ceda_request` waits Reset + 2 seconds before the next call.
  - Status: confirmed. Reset counts down in seconds: two calls 19 s apart on 2026-10-10 returned 3600, then 3581.
    - what:countdown is confirmed 
    -evidence : two calls, 19 seconds apart: 3600, then 3581, on 2026-10-10

### Request strategy
- One request per state × commodity × endpoint, covering 2018-01-01 to today.
- Verified no truncation **for Rajasthan only**: the Jaipur rows inside the Rajasthan pull (4,677) are identical to a Jaipur-only pull. Larger states (Uttar Pradesh, 71 districts) are untested, so the client checks every response.
- Full pull is about 30 requests.
### Measured coverage (Rajasthan onion sample)
- 55,368 price rows and 56,958 arrival rows.
- 2018-01-01 to 2025-10-30, so the data ends about 11 months before the access date.
- 28 of 33 districts report onion.


### Request body (prices, quantities)
- What: The POST body needs `commodity_id`, `state_id`, `district_id` (an explicit list of every district ID wanted), `from_date`, `to_date` (YYYY-MM-DD). Leaving out `district_id` has not been tested.
- Evidence: Saved probe request `prices_c23_s8_dALL_..._20261004T142642_http200.request.json` lists all 33 Rajasthan IDs (99–131). The same body shape gave 6/6 ok responses in the full pull on 2026-10-14.
- So what: The client builds each state's district list from `/agmarknet/geographies`.
- Status: Confirmed.

### API key expiry
- What: API keys expire. The exact lifetime is unknown.
- Evidence: Key generated 2026-10-04 (`.env` last written that day), worked on 2026-10-10, rejected on 2026-10-14 with HTTP 401 and the message "Api key expired". A new key was generated on 2026-10-14.
- So what: Renew the key before every pull; Phase 2's monthly backfill must allow for this. The client now logs CEDA's error message on any 4xx/5xx.
- Status: Lifetime between 6 and 10 days, not confirmed. Note the date the current key stops working.

### Server timeout (HTTP 504) uses quota
- What: Requests that take longer than ~60 s return HTTP 504. A 504 still counts against the 40/hour quota, even though it carries no RateLimit headers.
- Evidence: Full pull on 2026-10-14. Quota was 31 when the UP requests began; after 31 attempts that all returned 504 at ~60 s, the next request got HTTP 429 with `RateLimit-Remaining` = 0.
- So what: The client does not retry a 504 (the cause is request size, not a blip) and stops after 3 consecutive failures. Every request must be sized to finish well under 60 s.
- Status: Confirmed.

### Query speed differs by state
- What: CEDA returns data at very different speeds for different states.
- Evidence: Rajasthan, onion prices, 2018 to latest: 55,368 rows in ~50 s (~1,100 rows/s), 2026-10-14. Uttar Pradesh, 5 districts, 2024: 4,842 rows in 43.0 s (~112 rows/s), 2026-10-15. Jaipur, 1 month: 56 rows in 6.1 s.
- So what: Size requests for each state from a timing probe, not from Rajasthan's speed.
- Status: Confirmed for UP. Madhya Pradesh, Gujarat and Maharashtra not yet timed.

### Website download
- Tested and not used; see D-014.

### Query speed (revised 2026-10-17)
- What: Most of a request's time appears to be a fixed cost that depends on the state, not on the rows returned. Rajasthan is fast; Maharashtra and Uttar Pradesh are slow.
- Evidence:
  | Request | Rows | Time |
  |---|---|---|
  | Jaipur (RJ), 1 month | 56 | 6.1 s |
  | Rajasthan, all districts, 2018 to latest | 55,368 | ~50 s |
  | UP, 5 districts, 2024 | 4,842 | 43.0 s |
  | Nashik (MH), 2024 | 4,207 | 46.5 s |
  | Nashik (MH), Jan 2024 | 366 | 36.9 s |
- So what: Splitting by date does not bring Maharashtra requests below ~37 s. Group a state's districts into one request so the fixed cost is paid once; keep each request to roughly 4,000–5,000 rows so it finishes under 60 s.
- Status: Confirmed for Maharashtra. UP 1-month not timed; Madhya Pradesh and Gujarat not timed.

## 2. Kaggle raw Agmarknet scrape (reconciliation only)
To be completed.

## 3. DataMeet district boundaries (distances)
To be completed.