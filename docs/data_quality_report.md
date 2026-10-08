# Data Quality Report

Status: Week 1 exploration findings (Rajasthan onion sample, CEDA API, pulled 2026-10-04).
Full row counts (in → mapped → quarantined → loaded) are added in Week 2.

## 1. Issues found during exploration

### 1.1 Jaipur (F&V) reporting gap, 2020–2022
- **What:** market 273, Jaipur's main mandi by volume, has 27 / 55 / 63 onion price rows in
  2020 / 2021 / 2022, against 139–184 in other years.
- **Evidence:** rows per market per year, Jaipur onion pull 2018-01-01 to 2025-10-30.
- **So what:** Comparisons of supply mandis against Jaipur's main mandi have very few same-day pairs in 2020–22, so any "cheaper than Jaipur" saving for those years has wide uncertainty; we may need a backup Jaipur benchmark (e.g. Chomu or a district-level price) for that period.
- **Status:** confirmed for onion; check tomato and potato in profiling.

### 1.2 Markets and districts that never report onion
- **What:** markets 274 Chomu (Grain) and 2861 Janta Market are listed for Jaipur but have
  no onion rows in 2018–2025. 5 of 33 Rajasthan districts have no onion data:
  Dhaulpur, Dausa, Bundi, Banswara, Jhalawar.
- **Evidence:** market list vs price pull (`isin` check); district list vs Rajasthan pull.
- **So what:** These markets and districts can't be candidates in the "where to buy" comparison and are excluded, not treated as zero prices.
- **Status:** confirmed for onion.

### 1.3 Markets that start reporting late
- **What:** Bassi (3151) first appears in 2020; Kotputli (1545) in 2024.
- **Evidence:** rows per market per year, Jaipur onion pull.
- **So what:** A Jaipur average across years would mix in markets that joined part-way, so a change over time could reflect which markets report rather than a real price change; trends should be compared market by market or on a fixed set of markets.
- **Status:** confirmed for Jaipur onion.

### 1.4 Duplicate market-days with different prices
- **What:** 3 of 55,368 Rajasthan onion price rows share a date and market with another row
  but have a different price: Karauli (1186) on 2019-03-26 and 2019-03-27
  (modal ₹3.1 vs ₹11.4/kg), Jhunjhunun (278) on 2023-01-23 (₹12 vs ₹10/kg).
- **Evidence:** `duplicated(['date', 'market_id'], keep=False)` on the Rajasthan pull.
- **Likely cause:** different varieties or grades with the labels removed by the API.
- **Proposed handling (Week 2):** quarantine with reason code `DUP_UNLABELED_VARIETY`; do not average.
- **So what:** Too rare to change any result, but averaging a ₹3/kg row with an ₹11/kg row would create a ₹7/kg price that never existed; quarantining keeps every loaded price real and traceable.

### 1.5 Missing min and max prices
- **What:** `min_price` missing in 1 row, `max_price` in 4 rows, of 55,368. `modal_price` is never missing.
- **Evidence:** `isna().sum()` on the Rajasthan pull.
- **Proposed handling (Week 2):** keep the rows (modal is present); flag the missing field.
- **So what:** No effect on the main analysis, which uses modal price; it only affects min–max spread measures, which simply skip these 5 rows.

### 1.6 Arrivals missing statewide in June–July 2024
- **What:** 96.8% of priced market-days have arrivals overall, but in 2024 only about 80% do.
  1,438 of the 1,496 price-only market-days in 2024 fall in June–July, spread evenly across
  markets (each missing about 18–26% of its 2024 days).
- **Evidence:** outer join of prices and arrivals on date + market; breakdown by year,
  market and month.
- **Proposed handling (Week 2/3):** treat June–July 2024 arrivals as missing, never as zero.
- **So what:** Treating the gap as zero would fake a supply collapse in mid-2024 and distort the supply-vs-price analysis, so those months are excluded from any arrivals-based analysis.
- **Status:** confirmed for Rajasthan onion; check other states and commodities.

### 1.7 Arrivals may be under-reported
- **What:** Jaipur (F&V) shows a median of about 30 tonnes of onion per reporting day in
  January 2024, which looks low for a city of several million people.
- **Evidence:** median quantity per market, Jaipur onion, January 2024.
- **So what:** Arrivals can show how supply changes over time, but not how much onion Jaipur actually consumes, so we use them for trends and associations only, never as absolute volumes.
- **Status:** suspicion only, not confirmed.

### 1.8 Data ends on 2025-10-30
- **What:** the latest date in the Rajasthan onion pull is 2025-10-30, about 11 months
  before the access date.
- **Evidence:** `max()` of `date` on the Rajasthan price and arrivals pulls.
- **So what:** Every finding describes January 2018 to October 2025; in Phase 1, "is today's price abnormal?" is tested on historical data, not live prices, and the README must state the window clearly.

## 2. Questions for the data owner (CEDA)
1. How does the API collapse multiple varieties and grades into one price per market-day?
2. Were June–July 2024 arrivals not reported by Agmarknet, or lost in processing?
3. Why does the data end on 2025-10-30, and when is the next update expected?
4. Why do a few market-days still have two rows with different prices?

## 3. Row counts, quarantine and reconciliation
To be completed in Week 2.