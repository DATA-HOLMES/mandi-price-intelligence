# Decision Log

Every non-obvious decision, with date and reason. Newest at the bottom.

---

### D-001 · 2026-10-02 · Phase 1 scope
- **Decision:** Onion, Tomato, Potato; Rajasthan (Jaipur = home market) plus Maharashtra, Madhya Pradesh, Gujarat, Uttar Pradesh as supply states; January 2018 to latest available month.
- **Reason:** These three are the highest-volume weekly purchases for the target buyer and are known for sharp price swings. The window includes COVID-era disruption and the 2023 tomato spike, which the spike detector must be validated against.
- **Alternatives considered:** All-India scope (too broad to analyse well in 4 weeks); more commodities (dilutes the story).
- **Revisit when:** Week 1 profiling shows whether these states actually supply Jaipur's mandis.

### D-002 · 2026-10-02 · CEDA as primary historical source; Kaggle only for reconciliation
- **Decision:** Use CEDA Agri Market Data (Ashoka University) for the historical series. Use the raw Agmarknet Kaggle scrape (Oct 2024 to Aug 2025) only to cross-check CEDA on overlapping months.
- **Reason:** CEDA offers a long mandi-level history mapped to districts; the Kaggle scrape covers about 11 months only. Reconciliation shows how far CEDA's cleaning changed the raw data.
- **Alternatives considered:** Scraping Agmarknet directly (slow, fragile, and CEDA has already done it).
- **Revisit when:** CEDA access terms, coverage and API limits are confirmed in Week 1.

### D-003 · 2026-10-02 · Price units
- **Decision:** Store prices in ₹/quintal (source unit); show ₹/kg (÷100) in all business-facing outputs.
- **Reason:** Storing the source unit avoids conversion errors in the pipeline; buyers think in ₹/kg.

### D-004 · 2026-10-02 · Buyer interview skipped for now
- **Decision:** No interview with a real purchase manager in Phase 1 for now.
- **Reason:** Time. Listed as a limitation in the README; may be added later.
- **Consequence:** Assumptions about buying behaviour (weekly purchases, commission %, wastage %) are stated as assumptions, not validated facts.

### D-005 · 2026-10-02 · PostgreSQL 18.6 instead of 16
- **Decision:** Use the installed PostgreSQL 18.6.
- **Reason:** Every feature the project uses (window functions, PERCENTILE_CONT, COPY, constraints, views) exists in both versions; downgrading adds risk for no benefit.

### D-006 · 2026-10-02 · Library versions
- **Decision:** `requirements.txt` uses minimum versions (`>=`) during development; exact versions will be pinned at the end of Phase 1.
- **Reason:** Get bug fixes while building; guarantee identical rebuilds once published.

### D-007 · 2026-10-02 · Provisional thresholds
- **Decision:** Starting thresholds in `config/settings.yaml` (fuzzy match 92/80, scale error 8×, minimum 100 reporting days per year, spike z = 3.0 over 45 days, road factor 1.3).
- **Reason:** Reasonable starting points only. Each will be tested against real data (Weeks 1–3), and any change gets its own entry here.

### D-008: Use only the documented CEDA API; trust real responses over the docs
- **Date:** 2026-10-04
- **Decision:** All CEDA data is pulled from the official, key-based API at
  `https://api.ceda.ashoka.edu.in/v1`. When the Swagger documentation and the real
  responses disagree, the code follows the real responses.
- **Reason:** This API is the one covered by CEDA's API terms of use, so using it keeps
  the project within the licence. During probing, the Swagger examples turned out to be
  wrong in several places (response wrapper, field names, `/geographies` parameters), so
  the documentation alone can't be trusted for parsing.
- **Alternatives considered:**
  - *The portal's internal endpoint (`agmarknet.ceda.ashoka.edu.in/api/`)*, used by some
    third-party projects. Rejected: it's undocumented, not covered by the API terms, and
    could change without notice.
  - *Manual CSV downloads from the portal.* Rejected: not reproducible from code, and
    slow for 5 states × 3 commodities × 8 years.
- **Status:** Final.

### D-009: Keep commodity and state names in settings.yaml; look up IDs at run time
- **Date:** 2026-10-04
- **Decision:** `settings.yaml` lists commodities and states by name (e.g. `Onion`,
  `Rajasthan`). At run time the code finds each name's ID in CEDA's lookup lists
  (`/commodities`, `/geographies`) using an exact, case-insensitive match, and saves the
  lookups as a dated snapshot in `data/raw/ceda/`.
- **Reason:** IDs are CEDA's internal codes, not ours. Names keep the config readable to
  a person, and looking IDs up at run time means a renumbering by CEDA can't make us
  silently pull the wrong commodity. Exact matching is required because a substring search
  for "Onion" also returned Onion Green (358), and "Potato" returned Sweet Potato (152).
- **Alternatives considered:**
  - *Hard-code the IDs (23, 24, 78) in config or code.* Rejected: unreadable (`23` means
    nothing to a reviewer), and if an ID changed the pipeline would keep running on the
    wrong data with no error.
  - *Loose (substring or fuzzy) name matching.* Rejected: it matched the wrong
    commodities during probing.
- **Status:** Final. The code stops with an error if a name has zero or multiple exact matches.

### D-010: Fact table grain is date × market × commodity (no variety or grade)
- **Date:** 2026-10-04
- **Decision:** One row in the price fact table = one commodity at one market on one day.
  Variety and grade are not stored as dimensions from CEDA data.
- **Reason:** The CEDA API returns no variety or grade columns and, in the probed data,
  one row per date × market × commodity, even though the README says the underlying data
  is unique per variety and grade. A column we can't fill from the source shouldn't be in
  the model.
- **Alternatives considered:**
  - *Keep variety and grade columns filled with "All".* Rejected: it implies a breakdown
    that doesn't exist and would confuse anyone reading the schema.
  - *Use a source that has variety (the raw Agmarknet scrape).* Rejected for the main
    analysis: it only covers Oct 2024 to Aug 2025, not 2018 onwards.
- **Status:** Provisional. Revisit if reconciliation with the Kaggle data shows how CEDA
  collapses varieties, or if unlabeled duplicate rows turn out to be common in the full pull.

### D-011: Scratch notebooks are kept out of the repository
- **Date:** 2026-10-04
- **Decision:** Exploration notebooks live in `notebooks/scratch/`, which is gitignored.
  Only the clean, numbered notebooks (`01_profiling.ipynb` onwards) are committed.
- **Reason:** Scratch notebooks are trial and error, not deliverables. Their findings are
  recorded in `docs/` and their logic is rewritten cleanly in the final notebooks and
  `src/` modules.
- **Alternatives considered:**
  - *Commit the scratch notebooks.* Rejected: messy, out-of-order code in a public
    portfolio repo gives a poor impression and duplicates what the docs say.
- **Status:** Final.

### D-012: Pull one state × commodity × endpoint per request, throttled by rate-limit headers
- **Date:** 2026-10-04
- **Decision:** Each API request covers one state, one commodity and one endpoint (prices
  or quantities) for the full date range, with all the state's districts in one request.
  The client reads `RateLimit-Remaining` and `RateLimit-Reset` and waits for the window to
  reset when the budget runs out.
- **Reason:** The API allows 40 requests per hour. A whole-state request for Rajasthan
  onion (2018 to Oct 2025) returned 55,368 price rows with no truncation: its Jaipur rows
  were identical to a Jaipur-only request. This makes the full pull about 30 requests.
- **Alternatives considered:**
  - *Monthly requests.* Rejected: about 2,900 requests (5 states × 3 commodities × ~96
    months × 2 endpoints), roughly 72 hours at 40/hour.
  - *One request per district.* Rejected: about 1,300 requests, roughly 32 hours.
  - *A fixed delay between requests.* Rejected: the headers tell us exactly when the
    budget refills, so guessing a delay is either too slow or risks HTTP 429 errors.
- **Status:** Provisional. Truncation is verified for Rajasthan only. If a larger state
  (e.g. Uttar Pradesh, 71 districts) fails the checks, split that state into smaller
  district groups.

### D-013: The analysis window ends at CEDA's last available date
- **Date:** 2026-10-08
- **Decision:** Phase 1 covers 2018-01-01 to the latest date in the CEDA data (measured as
  2025-10-30 for Rajasthan onion). `end_date` stays `null` in `settings.yaml`, meaning
  "latest available".
- **Reason:** CEDA's data ends about 11 months before the access date. Using what exists
  keeps every number traceable to one consistent source.
- **Alternatives considered:**
  - *Fill the gap to today from the data.gov.in daily API.* Rejected for Phase 1: that's a
    second, differently processed source and belongs to the Phase 2 live pipeline.
  - *Hard-code an end date.* Rejected: when CEDA updates, the window should extend
    automatically.
- **Status:** Final for Phase 1. The exact end date is re-measured on the full pull and
  reported in the README.