# Dutch Football Scouting Platform (Eredivisie + Eerste Divisie)

A Streamlit scouting dashboard for the two Dutch professional leagues: the
Eredivisie (2022/23 – 2025/26) and the Eerste Divisie (2020/21 – 2026/27, the last one in progress).
Built on Wyscout player data, possession-adjusted (PAdj) per-90 metrics
(possession from FotMob for the Eredivisie and Sofascore for the Eerste
Divisie), and transfer history scraped from Transfermarkt. Pick the league in
the sidebar; every scouting tab then works on that league.

## What's inside

- **Player Profile, Rankings, Radar Charts, Advanced Search, Similarity,
  Z-Score, Market Comparison, Custom Dashboard** — the same scouting toolkit
  as the author's other league dashboards, rebuilt for a single-league,
  multi-season dataset (percentiles are computed within position & season,
  not across leagues).
- **Transfers** — every arrival at an Eredivisie club (this tab and the next
  always cover the Eredivisie, whichever league is selected) across the 4 seasons,
  with the fee actually paid (scraped from Transfermarkt), filterable by
  season, club, position and fee type.
- **Transfer Deep Dive** — two independent signals per transfer: market value
  over time (works for any transfer, tells you *whether* it worked) and a
  pillar-by-pillar before/after comparison for the ~160 transfers between two
  Eredivisie clubs (tells you *why*, since real before/after Wyscout data
  exists for those).

## Data pipeline

```
build_possession_eerste_divisie.py  # Sofascore possession per Eerste Divisie team and season
process_data.py          # Wyscout -> minutes filter, PAdj/OPAdj, per-pillar ratings (both leagues)
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
- Percentiles are computed within each league, position group and season, not
  globally — a CB is only ever compared to other CBs of the same league and
  season. A score in the Eerste Divisie is not comparable to one in the
  Eredivisie.
- Eerste Divisie possession is the average of each team's per-match possession
  (Sofascore); for the Eredivisie this reproduces the FotMob season figure to
  within 0.1 points. The four reserve sides (Ajax II, PSV II, AZ II, Utrecht II)
  are part of the Eerste Divisie and are kept.
- The Eerste Divisie 2026/27 season is still being played, so the minutes bar is
  scaled to the games each team has played (900 minutes over 38 games = 23.7
  minutes per game). Samples are small and percentiles will move; its
  possession is a snapshot (rerun `build_possession_eerste_divisie.py` after
  updating the embedded 2026/27 averages, and `process_data.py`).
