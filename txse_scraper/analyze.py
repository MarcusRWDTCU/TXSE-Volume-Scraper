from __future__ import annotations
import argparse,csv
from datetime import date,timedelta
from pathlib import Path

def f(v):
    try:return float(v)
    except:return 0.0
def money(v):
    return f"${v/1e9:,.2f}bn" if abs(v)>=1e9 else (f"${v/1e6:,.2f}m" if abs(v)>=1e6 else f"${v:,.0f}")
def n(v):
    return f"{v/1e9:,.2f}bn" if abs(v)>=1e9 else (f"{v/1e6:,.2f}m" if abs(v)>=1e6 else f"{v:,.0f}")
def load(path,start,end):
    with path.open(newline="",encoding="utf-8") as x: rows=[r for r in csv.DictReader(x) if start<=date.fromisoformat(r["trade_date"])<=end]
    return sorted(rows,key=lambda r:r["trade_date"])
def report(rows,start,end):
    if not rows:return f"# TXSE Volume Analysis\n\nNo observations found for {start} through {end}.\n"
    shares=[f(r.get("share_volume")) for r in rows]; dollars=[f(r.get("dollar_volume")) for r in rows]; trades=[f(r.get("trade_count")) for r in rows]
    ts,td,tt=sum(shares),sum(dollars),sum(trades); peak=max(rows,key=lambda r:f(r.get("share_volume"))); first,last=shares[0],shares[-1]; change=((last/first)-1)*100 if first else 0
    tape={t:sum(f(r.get(f"tape_{t.lower()}_volume")) for r in rows) for t in "ABC"}; tape_d={t:sum(f(r.get(f"tape_{t.lower()}_notional")) for r in rows) for t in "ABC"}
    weighted_share=sum(f(r.get("market_share_pct"))*f(r.get("total_us_volume")) for r in rows)/sum(f(r.get("total_us_volume")) for r in rows) if sum(f(r.get("total_us_volume")) for r in rows) else 0
    lines=["# TXSE Volume Analysis","",f"**Period:** {rows[0]['trade_date']} to {rows[-1]['trade_date']} ({len(rows)} trading days)","","## Executive summary","",f"TXSE matched **{n(ts)} shares** representing **{money(td)} notional** across **{n(tt)} trades**.",f"Average daily volume was **{n(ts/len(rows))} shares** and average daily notional was **{money(td/len(rows))}**. Period-weighted U.S. market share was **{weighted_share:.3f}%**.",f"Peak volume was **{peak['trade_date']}** at **{n(f(peak.get('share_volume')))} shares**. First-to-last volume change: **{change:+.1f}%**.","","## Daily detail","","| Date | Shares | Notional | Trades | Mkt share | $/share | Shares/trade |","|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        sv,dv,tc=f(r.get("share_volume")),f(r.get("dollar_volume")),f(r.get("trade_count")); lines.append(f"| {r['trade_date']} | {n(sv)} | {money(dv)} | {n(tc)} | {f(r.get('market_share_pct')):.3f}% | ${dv/sv if sv else 0:,.2f} | {sv/tc if tc else 0:,.1f} |")
    lines += ["","## Tape mix","","| Tape | Shares | Share of TXSE volume | Notional |","|---|---:|---:|---:|"]
    for t in "ABC": lines.append(f"| {t} | {n(tape[t])} | {(tape[t]/ts*100 if ts else 0):.1f}% | {money(tape_d[t])} |")
    lines += ["","## Interpretation","","- **Scale:** evaluate shares and notional together; share count alone is biased toward lower-priced securities.","- **Market share:** the consolidated-share denominator makes TXSE growth comparable across high- and low-volume U.S. sessions.","- **Flow quality:** shares per trade distinguishes many small executions from blockier flow.","- **Tape mix:** A/B/C concentration shows where TXSE is gaining traction by listing universe.","- **Trend:** rolling weekly comparisons are more informative than a single session.","","Source: Cboe U.S. Equities Historical Market Volume (UTDF/CTS consolidated data). Cite Cboe Exchange, Inc. when publishing.",""]
    return "\n".join(lines)
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--input",default="data/txse_daily.csv");p.add_argument("--start");p.add_argument("--end");p.add_argument("--output",default="reports/latest.md");a=p.parse_args(argv);end=date.fromisoformat(a.end) if a.end else date.today();start=date.fromisoformat(a.start) if a.start else end-timedelta(days=7);text=report(load(Path(a.input),start,end),start,end);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text,encoding="utf-8");print(text);return 0
if __name__=="__main__":raise SystemExit(main())
