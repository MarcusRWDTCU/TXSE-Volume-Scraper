from __future__ import annotations

import argparse, csv, io
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import requests

URL = "https://cdn.cboe.com/resources/us/equities/market-statistics/historical-market-volume/market_history_{year}.csv"
TXSE = "Texas Stock Exchange (F)"
FIELDS = ["trade_date","share_volume","dollar_volume","trade_count","market_share_pct","total_us_volume","tape_a_volume","tape_b_volume","tape_c_volume","tape_a_notional","tape_b_notional","tape_c_notional","tape_a_trades","tape_b_trades","tape_c_trades","avg_dollars_per_share","avg_shares_per_trade","source","scraped_at_utc"]


def num(v, integer=False):
    if v is None or str(v).strip() == "": return None
    n = float(str(v).replace(",", "").replace("$", ""))
    return int(n) if integer else n


def fetch_year(year: int, timeout=45):
    r = requests.get(URL.format(year=year), timeout=timeout, headers={"User-Agent":"TXSEVolumeCollector/2.0"})
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def extract(rows, start: date, end: date):
    us_totals = {}
    for r in rows:
        d = date.fromisoformat(r["Day"])
        if start <= d <= end:
            us_totals[d] = us_totals.get(d, 0.0) + (num(r.get("Total Shares")) or 0)
    out = []
    for r in rows:
        if r.get("Market Participant") != TXSE: continue
        d = date.fromisoformat(r["Day"])
        if not start <= d <= end: continue
        sv, dv, tc = num(r["Total Shares"], True), num(r["Total Notional"]), num(r["Total Trade Count"], True)
        total_us = us_totals.get(d)
        out.append({
            "trade_date": d.isoformat(), "share_volume": sv, "dollar_volume": dv, "trade_count": tc,
            "market_share_pct": (sv / total_us * 100) if sv and total_us else None, "total_us_volume": total_us,
            "tape_a_volume": num(r["Tape A Shares"], True), "tape_b_volume": num(r["Tape B Shares"], True), "tape_c_volume": num(r["Tape C Shares"], True),
            "tape_a_notional": num(r["Tape A Notional"]), "tape_b_notional": num(r["Tape B Notional"]), "tape_c_notional": num(r["Tape C Notional"]),
            "tape_a_trades": num(r["Tape A Trade Count"], True), "tape_b_trades": num(r["Tape B Trade Count"], True), "tape_c_trades": num(r["Tape C Trade Count"], True),
            "avg_dollars_per_share": dv/sv if sv else None, "avg_shares_per_trade": sv/tc if tc else None,
            "source":"cboe_historical", "scraped_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return sorted(out, key=lambda x:x["trade_date"])


def upsert(records, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True); existing = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            existing = {r["trade_date"]:r for r in csv.DictReader(f)}
    for rec in records: existing[rec["trade_date"]] = {k:"" if rec.get(k) is None else str(rec.get(k)) for k in FIELDS}
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(existing[d] for d in sorted(existing))


def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--output",default="data/txse_daily.csv"); a=p.parse_args(argv)
    end=date.fromisoformat(a.end) if a.end else date.today(); start=date.fromisoformat(a.start) if a.start else end-timedelta(days=10)
    records=[]
    for year in range(start.year,end.year+1): records += extract(fetch_year(year),start,end)
    upsert(records,Path(a.output)); print(f"Upserted {len(records)} TXSE trading days: {start} through {end}"); return 0

if __name__ == "__main__": raise SystemExit(main())
