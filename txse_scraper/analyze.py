from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path


def _f(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0


def _fmt_money(v: float) -> str:
    if abs(v) >= 1e9: return f"${v/1e9:,.2f}bn"
    if abs(v) >= 1e6: return f"${v/1e6:,.2f}m"
    return f"${v:,.0f}"


def _fmt_num(v: float) -> str:
    if abs(v) >= 1e9: return f"{v/1e9:,.2f}bn"
    if abs(v) >= 1e6: return f"{v/1e6:,.2f}m"
    return f"{v:,.0f}"


def load(path: Path, start: date, end: date):
    with path.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if start <= date.fromisoformat(r["trade_date"]) <= end]
    return sorted(rows, key=lambda r: r["trade_date"])


def report(rows, start: date, end: date) -> str:
    if not rows:
        return f"# TXSE Volume Analysis\n\nNo TXSE observations found for {start} through {end}.\n"
    shares = [_f(r.get("share_volume")) for r in rows]
    dollars = [_f(r.get("dollar_volume")) for r in rows]
    trades = [_f(r.get("trade_count")) for r in rows]
    total_shares, total_dollars, total_trades = sum(shares), sum(dollars), sum(trades)
    peak = max(rows, key=lambda r: _f(r.get("share_volume")))
    tape_shares = {t: sum(_f(r.get(f"tape_{t.lower()}_volume")) for r in rows) for t in "ABC"}
    tape_dollars = {t: sum(_f(r.get(f"tape_{t.lower()}_notional")) for r in rows) for t in "ABC"}
    first, last = shares[0], shares[-1]
    change = ((last / first) - 1) * 100 if first else 0
    lines = [
        "# TXSE Volume Analysis", "",
        f"**Period:** {rows[0]['trade_date']} to {rows[-1]['trade_date']} ({len(rows)} trading days)", "",
        "## Executive summary", "",
        f"TXSE matched **{_fmt_num(total_shares)} shares** representing **{_fmt_money(total_dollars)} notional** across **{_fmt_num(total_trades)} trades** during the period.",
        f"Average daily volume was **{_fmt_num(total_shares/len(rows))} shares** and average daily notional was **{_fmt_money(total_dollars/len(rows))}**.",
        f"The highest-volume session was **{peak['trade_date']}** at **{_fmt_num(_f(peak.get('share_volume')))} shares**. Volume changed **{change:+.1f}%** from the first to the last observation.", "",
        "## Daily detail", "",
        "| Date | Shares | Notional | Trades | $/share | Shares/trade |", "|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        sv, dv, tc = _f(r.get("share_volume")), _f(r.get("dollar_volume")), _f(r.get("trade_count"))
        lines.append(f"| {r['trade_date']} | {_fmt_num(sv)} | {_fmt_money(dv)} | {_fmt_num(tc)} | ${(dv/sv if sv else 0):,.2f} | {(sv/tc if tc else 0):,.1f} |")
    lines += ["", "## Tape mix", "", "| Tape | Shares | Share of volume | Notional |", "|---|---:|---:|---:|"]
    for t in "ABC":
        pct = tape_shares[t] / total_shares * 100 if total_shares else 0
        lines.append(f"| {t} | {_fmt_num(tape_shares[t])} | {pct:.1f}% | {_fmt_money(tape_dollars[t])} |")
    lines += ["", "## Interpretation", "",
              "- **Scale:** use average daily shares and notional together; share count alone can be distorted by low-priced names.",
              "- **Flow quality:** average shares per trade helps distinguish many small prints from fewer blockier executions.",
              "- **Tape concentration:** the A/B/C split shows where TXSE is gaining traction by listing universe.",
              "- **Trend:** compare subsequent rolling weeks against this baseline rather than over-interpreting one session.", "",
              "Source: Cboe U.S. Equities Historical Market Volume (UTDF/CTS consolidated data). Published analysis should cite Cboe Exchange, Inc.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Generate TXSE volume analysis")
    p.add_argument("--input", default="data/txse_daily.csv")
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--output", default="reports/latest.md")
    a = p.parse_args(argv)
    end = date.fromisoformat(a.end) if a.end else date.today()
    start = date.fromisoformat(a.start) if a.start else end - timedelta(days=7)
    rows = load(Path(a.input), start, end)
    text = report(rows, start, end)
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
