# TXSE Volume Scraper & Analytics

Daily Cboe history for Texas Stock Exchange (F), plus Nasdaq (Q) comparison, volume diagnostics and ORC graphics.

![TXSE dashboard](reports/charts/txse_dashboard.png)

- [Volume build-up, anomalies and trading behavior](reports/volume_behavior.md)
- [Standalone HTML dashboard](reports/txse_dashboard.html)
- [News review: 16 September 2026](reports/news_2026-09-16.md)
- [Weekly evolution](reports/weekly_evolution.md)
- [Daily observations](data/txse_daily.csv)
- [TXSE / Nasdaq venue comparison](data/txse_nasdaq_comparison.csv)
- [Statistical anomaly screen](data/txse_anomalies.csv)
- [Raw annual source and retrieval metadata](data/raw/)

## Run

```bash
pip install -r requirements.txt
python -m txse_scraper.history --start 2026-07-06
python -m txse_scraper.analyze
python -m txse_scraper.weekly
python -m txse_scraper.charts
python -m txse_scraper.diagnostics
pytest -q
```

GitHub Actions runs at 23:35 UTC Monday–Friday, on manual dispatch, and on changes to collector code, tests, requirements or the workflow. GitHub may delay scheduled execution. Each run refetches the annual source and upserts all TXSE observations from 6 July 2026, then commits refreshed data and reports. Cboe publication can lag the latest session. Report dates state the actual last observation. News is a dated editorial review, not automatically refreshed by the volume collector.

## Definitions and limitations

Daily shares, USD notional and trade counts are broken down by listing Tape A/B/C. Market shares use ratios of summed volumes. `lit_market_share_pct` is retained for compatibility but means **exchange-only share excluding FINRA/TRF**, not exclusively displayed liquidity. Tape C is the Nasdaq-listed universe; NASDAQ (Q) is an execution venue. They are different concepts.

The request window starts on the announced launch date, 6 July. The currently retrieved source first reports TXSE on 10 July. Missing observations are not filled with zero. Anomaly flags use the previous 20 observed sessions, excluding the current observation; a robust absolute z-score above 3.5 is a descriptive flag, not evidence of misconduct. The startup regime limits statistical interpretation. Use ADV and matched-length session windows for incomplete or holiday weeks.

These aggregates do not identify traders, buy/sell aggression, symbols, order-book liquidity, HFT share, retail share or execution quality.

Source: [Cboe Exchange, Inc., Historical Market Volume](https://www.cboe.com/markets/us/equities/market-statistics/historical-market-volume), based on UTDF/CTS feeds. Raw files carry a retrieval timestamp, source URL and SHA-256 hash. Citation: Cboe Exchange, Inc.
