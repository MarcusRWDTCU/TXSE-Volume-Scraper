from __future__ import annotations

import argparse, csv
from pathlib import Path
import matplotlib.pyplot as plt


def f(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0


def load(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def save_line(x, y, title, ylabel, path):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(x, y, marker="o")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Week starting")
    ax.grid(True, alpha=0.25)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="data/txse_weekly.csv")
    p.add_argument("--outdir",default="reports/charts")
    a=p.parse_args(argv)
    rows=load(Path(a.input))
    out=Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    x=[r["week_start"] for r in rows]
    save_line(x,[f(r["avg_daily_volume"])/1e6 for r in rows],"TXSE Average Daily Share Volume","ADV (millions of shares)",out/"weekly_adv.png")
    save_line(x,[f(r["avg_daily_notional"])/1e6 for r in rows],"TXSE Average Daily Notional","Average daily notional ($m)",out/"weekly_notional.png")
    save_line(x,[f(r["consolidated_market_share_pct"]) for r in rows],"TXSE Consolidated U.S. Market Share","Market share (%)",out/"weekly_consolidated_share.png")
    save_line(x,[f(r["lit_market_share_pct"]) for r in rows],"TXSE Share of Lit Exchange Volume","Lit exchange share (%)",out/"weekly_lit_share.png")
    print(f"Generated charts in {out}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
