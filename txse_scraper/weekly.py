from __future__ import annotations

import argparse, csv
from collections import defaultdict
from datetime import date
from pathlib import Path


def f(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0


def fmt_num(v):
    if abs(v) >= 1e9: return f"{v/1e9:.2f}bn"
    if abs(v) >= 1e6: return f"{v/1e6:.2f}m"
    if abs(v) >= 1e3: return f"{v/1e3:.1f}k"
    return f"{v:.0f}"


def fmt_money(v):
    if abs(v) >= 1e9: return f"${v/1e9:.2f}bn"
    if abs(v) >= 1e6: return f"${v/1e6:.2f}m"
    return f"${v:,.0f}"


def load(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def aggregate(rows):
    groups = defaultdict(list)
    for r in rows:
        d = date.fromisoformat(r["trade_date"])
        monday = d.fromordinal(d.toordinal() - d.weekday())
        groups[monday].append(r)

    out = []
    prev_adv = None
    for monday in sorted(groups):
        rs = sorted(groups[monday], key=lambda r:r["trade_date"])
        shares = sum(f(r.get("share_volume")) for r in rs)
        notional = sum(f(r.get("dollar_volume")) for r in rs)
        trades = sum(f(r.get("trade_count")) for r in rs)
        total_us = sum(f(r.get("total_us_volume")) for r in rs)
        lit_us = sum(f(r.get("lit_us_volume")) for r in rs)
        a = sum(f(r.get("tape_a_volume")) for r in rs)
        b = sum(f(r.get("tape_b_volume")) for r in rs)
        c = sum(f(r.get("tape_c_volume")) for r in rs)
        days = len(rs)
        adv = shares / days if days else 0
        wow_adv = ((adv / prev_adv) - 1) * 100 if prev_adv else None
        rec = {
            "week_start": monday.isoformat(), "week_end": rs[-1]["trade_date"], "trading_days": days,
            "share_volume": shares, "avg_daily_volume": adv, "dollar_volume": notional,
            "avg_daily_notional": notional/days if days else 0, "trade_count": trades,
            "consolidated_market_share_pct": shares/total_us*100 if total_us else 0,
            "lit_market_share_pct": shares/lit_us*100 if lit_us else 0,
            "wow_adv_pct": wow_adv,
            "tape_a_pct": a/shares*100 if shares else 0,
            "tape_b_pct": b/shares*100 if shares else 0,
            "tape_c_pct": c/shares*100 if shares else 0,
        }
        out.append(rec)
        prev_adv = adv
    return out


FIELDS = ["week_start","week_end","trading_days","share_volume","avg_daily_volume","dollar_volume","avg_daily_notional","trade_count","consolidated_market_share_pct","lit_market_share_pct","wow_adv_pct","tape_a_pct","tape_b_pct","tape_c_pct"]


def write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)


def write_report(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# TXSE Weekly Evolution", "", "Weekly aggregation of Texas Stock Exchange (F) trading activity.", "", "| Week | Days | Shares | ADV | Notional | Trades | Consolidated share | Lit exchange share | WoW ADV | Tape A | Tape B | Tape C |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        wow = "—" if r["wow_adv_pct"] is None else f"{r['wow_adv_pct']:+.1f}%"
        lines.append(f"| {r['week_start']} to {r['week_end']} | {r['trading_days']} | {fmt_num(r['share_volume'])} | {fmt_num(r['avg_daily_volume'])} | {fmt_money(r['dollar_volume'])} | {fmt_num(r['trade_count'])} | {r['consolidated_market_share_pct']:.3f}% | {r['lit_market_share_pct']:.3f}% | {wow} | {r['tape_a_pct']:.1f}% | {r['tape_b_pct']:.1f}% | {r['tape_c_pct']:.1f}% |")
    lines += ["", "**Definitions:** Consolidated market share uses total U.S. consolidated reported volume, matching Cboe's published market-share convention. Lit exchange share excludes FINRA/TRF off-exchange volume and compares TXSE only with exchange-matched volume.", "", "Source: Cboe Global Markets U.S. Equities Historical Market Volume.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="data/txse_daily.csv")
    p.add_argument("--csv",default="data/txse_weekly.csv")
    p.add_argument("--report",default="reports/weekly_evolution.md")
    a=p.parse_args(argv)
    weekly = aggregate(load(Path(a.input)))
    write_csv(weekly,Path(a.csv)); write_report(weekly,Path(a.report))
    print(f"Generated {len(weekly)} weekly observations")
    return 0

if __name__ == "__main__": raise SystemExit(main())
