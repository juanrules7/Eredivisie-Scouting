# Eredivisie Scouting Platform

A Streamlit scouting dashboard for the Dutch Eredivisie, covering four seasons
(2022/23 – 2025/26). Built on Wyscout player data, possession-adjusted (PAdj)
per-90 metrics scraped from FotMob, and transfer history scraped from
Transfermarkt.

## What's inside

- **Player Profile, Rankings, Radar Charts, Advanced Search, Similarity,
  Z-Score, Market Comparison, Custom Dashboard** — the same scouting toolkit
  as the author's other league dashboards, rebuilt for a single-league,
  multi-season dataset (percentiles are computed within position & season,
  not across leagues).
- **Transfers** — every arrival at an Eredivisie club across the 4 seasons,
  with the fee actually paid (scraped from Transfermarkt), filterable by
  season, club, position and fee type.
- **Transfer Deep Dive** — two independent signals per transfer: market value
  over time (works for any transfer, tells you *whether* it worked) and a
  pillar-by-pillar before/after comparison for the ~160 transfers between two
  Eredivisie clubs (tells you *why*, since real before/after Wyscout data
  exists for those).

## Data pipeline

```
process_data.py          # Wyscout -> minutes filter, PAdj/OPAdj, per-pillar ratings
scrape_transfers.py       # Transfermarkt club arrivals per season -> data/transfers_raw.json
build_transfer_report.py  # matches transfers to Wyscout players
scrape_market_values.py   # Transfermarkt market value history per player
```

Run them in that order (after placing the raw Wyscout exports in `data/raw/`)
to regenerate everything, then:

```
streamlit run app.py
```

## Methodology notes

- Minimum 900 minutes played per season.
- All per-90 stats are possession-adjusted (PAdj/OPAdj) to a neutral 50%
  possession baseline.
- Percentiles are computed within each position group and season, not
  globally — a CB is only ever compared to other CBs that season.
