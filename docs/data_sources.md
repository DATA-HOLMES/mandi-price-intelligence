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
- 40 requests per hour, fixed window starting at the first call.
- Headers: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`.
- HTTP 429 when exceeded.
### Request strategy
- One request per state × commodity × endpoint, covering 2018-01-01 to today.
- Verified no truncation **for Rajasthan only**: the Jaipur rows inside the Rajasthan pull (4,677) are identical to a Jaipur-only pull. Larger states (Uttar Pradesh, 71 districts) are untested, so the client checks every response.
- Full pull is about 30 requests.
### Measured coverage (Rajasthan onion sample)
- 55,368 price rows and 56,958 arrival rows.
- 2018-01-01 to 2025-10-30, so the data ends about 11 months before the access date.
- 28 of 33 districts report onion.

## 2. Kaggle raw Agmarknet scrape (reconciliation only)
To be completed.

## 3. DataMeet district boundaries (distances)
To be completed.