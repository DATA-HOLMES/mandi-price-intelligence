# Project Brief: Mandi Price Intelligence

## Problem statement
Restaurant chains and wholesalers buy commodities such as onion, tomato and potato from the nearest mandi out of habit, even though prices swing by season and differ between mandis, so they end up overpaying. This project tells them which mandi is cheapest after transport cost, which months are cheapest to buy, and whether today's price is spiked.

**In one line:** Google Flights for vegetables. It shows when prices are usually low, where it's cheaper, and whether today's price is unusually high.

## User
**Purchase manager of a mid-sized Jaipur restaurant chain or wholesaler.**
- Buys onion, tomato and potato every week.
- Buys today through habit and phone calls with commission agents, not data.
- Cannot easily tell whether another mandi would be cheaper after transport, when to stock up, or whether today's price is a spike.

## The three questions
1. **Where to buy:** Which supply mandis are cheaper than Jaipur *after* transport cost, and by how much (₹/kg)?
2. **When to buy:** Which months are usually cheapest and costliest for each commodity?
3. **Is today abnormal:** Is today's price normal, or a spike worth waiting out?

## Scope (Phase 1)
| Item | In scope |
|---|---|
| Commodities | Onion, Tomato, Potato |
| Geography | Rajasthan (Jaipur = home market) + Maharashtra, Madhya Pradesh, Gujarat, Uttar Pradesh as supply states |
| Time window | January 2018 to the latest available month |
| Price unit | Stored in ₹/quintal (source unit); shown in ₹/kg in all business outputs |
| Main data source | CEDA Agri Market Data (Ashoka University), cross-checked against a raw Agmarknet sample |

Scope changes are recorded in `docs/decision_log.md`.

## Success criteria
1. **When:** for each commodity, the cheapest and costliest months to buy, backed by multi-year data, with how stable the pattern is across years.
2. **Where:** for a Jaipur buyer, which supply mandis are cheaper after transport cost and by how much, in ₹/kg with a 95% confidence interval.
3. **Abnormal:** a spike-detection method that correctly flags known historical spikes (e.g. tomato, mid-2023), reporting how early it flags them and how many false alarms it raises.
4. **Data quality:** a documented cleaning process with counts at every stage (rows in, quarantined by reason, loaded) and a reconciliation between two sources.

## Deliverables
- Clean, modelled data in PostgreSQL (star schema) with post-load quality checks
- SQL analysis files and views
- Statistical notebooks: seasonality, market comparison, spike detection
- Excel landed-cost calculator for a non-technical buyer
- 5-page Power BI dashboard (+ PDF export)
- Memo-style README that leads with a numeric recommendation

## Out of scope (Phase 1)
- Price forecasting or machine-learning models
- Live or daily-updating data (Phase 2)
- Retail or consumer prices; only wholesale mandi prices
- Commodities beyond onion, tomato and potato
- Actual commission rates, negotiated prices or quality differences beyond what the data records

## Known limitations from the start
- CEDA data is already partly cleaned by its publisher; the reconciliation measures how much.
- Distances are straight-line estimates × a road factor, not real routes.
- Transport, commission and wastage rates are assumptions, shown and editable in the Excel model.
- Arrivals (supply) data may be too sparse for analysis; checked in Week 1.
- Price–supply results are associations, not causal effects.
- No buyer interview yet; buying behaviour is assumed, not validated (see D-004).