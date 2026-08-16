from __future__ import annotations

import argparse
import csv
import io
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

URL = "https://cdn.cboe.com/resources/us/equities/market-statistics/historical-market-volume/market_history_{year}.csv"
TXSE_CODE = "F"

# Cboe has changed column labels over time. Normalize likely spellings here.
def _norm(s: str) -> str:
    return "".join(c.lower() for c in (s or "") if c.isalnum())


def _pick(row: dict[str, str], *names: str) -> str | None:
    lookup = {_norm(k): v for k, v in row.items()}
    for name in names:
        if _norm(name) in lookup:
            return lookup[_norm(name)]
    return None


def _number(value: str | None, integer: bool = False):
    if value is None or value.strip() == "":
        return None
    value = value.replace(",", "").replace("$", "").replace("%", "").strip()
    n = float(value)
    return int(n) if integer else n


def _parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unknown Cboe date format: {value}")


def fetch_year(year: int, timeout: int = 45) -> list[dict[str, str]]:
    r = requests.get(URL.format(year=year), timeout=timeout, headers={"User-Agent": "TXSEVolumeCollector/2.0"})
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def _is_txse(row: dict[str, str]) -> bool:
    exchange = _pick(row, "exchange", "exchange code", "participant", "participant code", "market center", "marketcenter")
    name = _pick(row, "exchange name", "market center name", "marketcentername", "venue", "name")
    return (exchange or "").strip().upper() == TXSE_CODE or "texas stock exchange" in (name or "").lower()


def _tape(row: dict[str, str]) -> str:
    return (_pick(row, "tape", "listing tape", "listed tape", "security tape") or "").strip().upper().replace("TAPE", "").strip()


def _value(row: dict[str, str], kind: str):
    aliases = {
        "shares": ("shares", "volume", "matched shares", "matched volume", "share volume"),
        "notional": ("notional", "notional value", "dollar volume", "dollar value", "value"),
        "trades": ("trades", "trade count", "number of trades", "transactions"),
    }
    return _number(_pick(row, *aliases[kind]), integer=(kind != "notional"))


def extract(rows: list[dict[str, str]], start: date, end: date) -> list[dict[str, object]]:
    grouped: dict[date, dict[str, object]] = {}
    for row in rows:
        if not _is_txse(row):
            continue
        raw_date = _pick(row, "date", "trade date", "trading date")
        if not raw_date:
            continue
        d = _parse_date(raw_date)
        if not start <= d <= end:
            continue
        tape = _tape(row)
        rec = grouped.setdefault(d, {"trade_date": d.isoformat(), "source": "cboe_historical"})
        shares, notional, trades = _value(row, "shares"), _value(row, "notional"), _value(row, "trades")
        # Some Cboe files have a total row, others only tape rows.
        if tape in {"A", "B", "C"}:
            rec[f"tape_{tape.lower()}_volume"] = shares
            rec[f"tape_{tape.lower()}_notional"] = notional
            rec[f"tape_{tape.lower()}_trades"] = trades
        else:
            if shares is not None: rec["share_volume"] = shares
            if notional is not None: rec["dollar_volume"] = notional
            if trades is not None: rec["trade_count"] = trades

    fields = ["share_volume", "dollar_volume", "trade_count"]
    for rec in grouped.values():
        for metric, suffix in (("volume", "share_volume"), ("notional", "dollar_volume"), ("trades", "trade_count")):
            if rec.get(suffix) is None:
                vals = [rec.get(f"tape_{t}_{metric}") for t in "abc"]
                if any(v is not None for v in vals):
                    rec[suffix] = sum(v or 0 for v in vals)
        sv, dv, tc = rec.get("share_volume"), rec.get("dollar_volume"), rec.get("trade_count")
        rec["avg_dollars_per_share"] = (dv / sv) if sv and dv is not None else None
        rec["avg_shares_per_trade"] = (sv / tc) if tc and sv is not None else None
        rec["scraped_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return [grouped[d] for d in sorted(grouped)]


FIELDS = [
    "trade_date", "share_volume", "dollar_volume", "trade_count",
    "tape_a_volume", "tape_b_volume", "tape_c_volume",
    "tape_a_notional", "tape_b_notional", "tape_c_notional",
    "tape_a_trades", "tape_b_trades", "tape_c_trades",
    "avg_dollars_per_share", "avg_shares_per_trade", "source", "scraped_at_utc",
]


def upsert(records: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict[str, str]] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["trade_date"]] = row
    for rec in records:
        existing[str(rec["trade_date"])] = {k: "" if rec.get(k) is None else str(rec.get(k)) for k in FIELDS}
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(existing[d] for d in sorted(existing))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Backfill TXSE daily shares, notional and trades from Cboe historical data")
    p.add_argument("--start", help="YYYY-MM-DD; default 10 calendar days ago")
    p.add_argument("--end", help="YYYY-MM-DD; default today")
    p.add_argument("--output", default="data/txse_daily.csv")
    a = p.parse_args(argv)
    end = date.fromisoformat(a.end) if a.end else date.today()
    start = date.fromisoformat(a.start) if a.start else end - timedelta(days=10)
    records = []
    for year in range(start.year, end.year + 1):
        records.extend(extract(fetch_year(year), start, end))
    upsert(records, Path(a.output))
    print(f"Upserted {len(records)} TXSE trading days: {start} through {end}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
