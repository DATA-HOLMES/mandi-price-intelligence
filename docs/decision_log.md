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