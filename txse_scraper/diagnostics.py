"""Reproducible ORC volume diagnostics. No inference of trader identity from prints."""
import csv, json, math, statistics, html
from pathlib import Path
from datetime import date
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from .weekly import aggregate

ROOT=Path('.')
BG='#f4f1e9'; INK='#171e24'; GOLD='#a47b37'; BLUE='#456c80'; GREY='#91999c'

def read(path):
    with Path(path).open() as f: return list(csv.DictReader(f))
def number(r,k): return float(r[k])
def summary(rows):
    s=lambda k:sum(number(r,k) for r in rows)
    return dict(start=rows[0]['trade_date'],end=rows[-1]['trade_date'],days=len(rows),adv=s('share_volume')/len(rows),adnv=s('dollar_volume')/len(rows),trades=s('trade_count')/len(rows),share=s('share_volume')/s('total_us_volume')*100,exchange_share=s('share_volume')/s('lit_us_volume')*100,size=s('share_volume')/s('trade_count'),price=s('dollar_volume')/s('share_volume'),tape_b=s('tape_b_volume')/s('share_volume')*100,tape_c=s('tape_c_volume')/s('share_volume')*100)
def anomalies(rows):
    out=[]
    for i,r in enumerate(rows):
        rec={'trade_date':r['trade_date']}
        for k in ['share_volume','dollar_volume','trade_count','market_share_pct','avg_shares_per_trade']:
            prev=[number(x,k) for x in rows[max(0,i-20):i]]
            z=None
            if len(prev)==20:
                med=statistics.median(prev); mad=statistics.median(abs(x-med) for x in prev)
                if mad: z=.67448975*(number(r,k)-med)/mad
            rec[k+'_robust_z']=z
        rec['flag']=any(v is not None and abs(v)>3.5 for k,v in rec.items() if k.endswith('_z'))
        out.append(rec)
    return out

def style(ax,title,ylabel):
    ax.set_facecolor(BG); ax.set_title(title,loc='left',fontsize=13,pad=15,fontweight='bold')
    ax.set_ylabel(ylabel,fontsize=10); ax.grid(axis='y',alpha=.18); ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)
    ax.spines[['left','bottom']].set_color('#b9b9b2')
    ax.tick_params(labelsize=9)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO,interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.'))

def main():
    rows=read('data/txse_daily.csv'); assert rows
    assert len({r['trade_date'] for r in rows})==len(rows)
    for r in rows:
        for total,suffix in [('share_volume','volume'),('dollar_volume','notional'),('trade_count','trades')]:
            assert math.isclose(number(r,total),sum(number(r,f'tape_{t}_{suffix}') for t in 'abc'),rel_tol=1e-9,abs_tol=.02),r['trade_date']
    weekly=aggregate(rows); last=summary(rows[-5:]); prev=summary(rows[-10:-5]); baseline=summary([r for r in rows if '2026-08-17'<=r['trade_date']<='2026-08-28'])
    flags=anomalies(rows)
    with open('data/txse_anomalies.csv','w') as f:
        w=csv.DictWriter(f,fieldnames=flags[0]);w.writeheader();w.writerows(flags)
    raw=read('data/raw/market_history_2026.csv')
    peers=[r for r in raw if rows[0]['trade_date']<=r['Day']<=rows[-1]['trade_date'] and r['Market Participant'] in ('NASDAQ (Q)','Texas Stock Exchange (F)')]
    with open('data/txse_nasdaq_comparison.csv','w') as f:
        w=csv.DictWriter(f,fieldnames=raw[0]);w.writeheader();w.writerows(peers)
    stats={'latest_5_sessions':last,'previous_5_sessions':prev,'aug_17_28_baseline':baseline,'history_days':len(rows),'latest_date':rows[-1]['trade_date'],'flagged_dates':[r['trade_date'] for r in flags if r['flag']]}
    Path('reports/diagnostics.json').write_text(json.dumps(stats,indent=2)+'\n')
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':INK,'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,'svg.fonttype':'none'})
    dates=[date.fromisoformat(r['trade_date']) for r in rows]
    fig,axs=plt.subplots(3,2,figsize=(16,14),facecolor=BG)
    fig.subplots_adjust(top=.76,bottom=.075,left=.075,right=.96,hspace=.55,wspace=.24)
    fig.text(.075,.954,'OPEN RANGE CAPITAL  /  MARKET STRUCTURE',fontsize=12,color=GOLD,weight='bold')
    fig.text(.075,.916,'TXSE: Mehr Volumen, mehr Abschlüsse.',fontsize=29,weight='bold')
    fig.text(.075,.882,f"{rows[0]['trade_date']} bis {rows[-1]['trade_date']}  |  {len(rows)} beobachtete Handelstage  |  Tagesdaten, kein Intraday-Orderflow",fontsize=11,color=BLUE)
    for x,big,label in [(.075,f"{last['adv']/1e6:.2f} Mio.",'Stück pro Tag · letzte 5 Sessions'),(.38,f"{last['share']:.3f} %",'US-Marktanteil · volumengewichtet'),(.68,f"{last['trades']/1000:.1f} Tsd.",'Abschlüsse pro Tag · letzte 5 Sessions')]:
        fig.text(x,.846,big,fontsize=23,weight='bold');fig.text(x,.822,label,fontsize=10)
    ax=axs[0,0];style(ax,'01  Stückzahl und laufender Aufbau','Mio. Stück / Tag')
    ax.bar(dates,[number(r,'share_volume')/1e6 for r in rows],color=BLUE,width=.8,alpha=.7,label='Tagesvolumen')
    roll=[sum(number(v,'share_volume') for v in rows[i-4:i+1])/5e6 if i>=4 else math.nan for i in range(len(rows))]
    ax.plot(dates,roll,color=GOLD,lw=2.2,label='5-Session-Durchschnitt');ax.legend(frameon=False,fontsize=9)
    ax=axs[0,1];style(ax,'02  Wachstum relativ zum Gesamtmarkt','Marktanteil (%)')
    ax.plot(dates,[number(r,'market_share_pct') for r in rows],color=INK,label='US gesamt',lw=2)
    ax.plot(dates,[number(r,'lit_market_share_pct') for r in rows],color=GOLD,label='Nur Börsen, ohne TRF',lw=2);ax.legend(frameon=False,fontsize=9)
    ax=axs[1,0];style(ax,'03  Dollarumsatz misst eine andere Dimension','Mio. USD / Tag')
    ax.plot(dates,[number(r,'dollar_volume')/1e6 for r in rows],color=INK,lw=2);ax.fill_between(dates,[number(r,'dollar_volume')/1e6 for r in rows],alpha=.12,color=GOLD)
    ax=axs[1,1];style(ax,'04  Mehr Abschlüsse','Tsd. Abschlüsse / Tag')
    ax.plot(dates,[number(r,'trade_count')/1000 for r in rows],color=BLUE,lw=2)
    ax=axs[2,0];style(ax,'05  Zusammensetzung nach Listing-Tape','Anteil am TXSE-Stückvolumen (%)')
    ax.stackplot(dates,*[[number(r,f'tape_{t}_volume')/number(r,'share_volume')*100 for r in rows] for t in 'abc'],colors=[INK,GOLD,BLUE],labels=['Tape A','Tape B','Tape C']);ax.set_ylim(0,100);ax.legend(frameon=True,facecolor=BG,fontsize=9,loc='upper right')
    ax=axs[2,1];style(ax,'06  Größe der einzelnen Ausführungen','Stück / Abschluss')
    ax.plot(dates,[number(r,'avg_shares_per_trade') for r in rows],color=GOLD,lw=2)
    fig.text(.075,.032,'Quelle: Cboe Exchange, Inc. · ORC-Berechnungen · Börsenanteil ist kein Maß für ausschließlich sichtbare Liquidität.',fontsize=10,color=BLUE)
    fig.text(.075,.014,'Abschlussgröße identifiziert weder Retail/HFT noch Kaufdruck. 06.–09.07.: keine TXSE-Zeilen in dieser Quelle; keine Nullsetzung.',fontsize=9,color=BLUE)
    Path('reports/charts').mkdir(exist_ok=True)
    for ext in ['png','svg']: fig.savefig(f'reports/charts/txse_dashboard.{ext}',dpi=170,facecolor=BG)
    plt.close(fig)
    lines=['# TXSE | Volume build-up und Trading Behavior','',f'Datenstand: {rows[-1]["trade_date"]}. News separat mit Recherche-Stichtag. Quelle: Cboe Exchange, Inc.','', '![ORC TXSE Dashboard](charts/txse_dashboard.png)','', '## Vergleich gleich langer Fenster','', '| Kennzahl | Vorherige 5 Sessions | Letzte 5 Sessions | Veränderung |','|---|---:|---:|---:|']
    for key,label,scale,unit in [('adv','Stück / Tag',1e6,' Mio.'),('adnv','USD / Tag',1e6,' Mio.'),('trades','Abschlüsse / Tag',1,'') ,('size','Stück / Abschluss',1,''),('price','USD / Stück',1,'')]:
        lines.append(f"| {label} | {prev[key]/scale:,.2f}{unit} | {last[key]/scale:,.2f}{unit} | {(last[key]/prev[key]-1)*100:+.2f}% |")
    lines += [f"| US-Marktanteil | {prev['share']:.4f}% | {last['share']:.4f}% | {(last['share']-prev['share'])*100:+.2f} bp |",'',f"Fenster: {prev['start']} bis {prev['end']} und {last['start']} bis {last['end']}. Quotienten werden aus Summen berechnet, nicht als ungewichtete Tagesmittel.",'','## Aufbau gegenüber der August-Basis','',f"Gegenüber 17.–28.08. ({baseline['days']} Sessions) stieg ADV um {(last['adv']/baseline['adv']-1)*100:.1f}%, Dollarumsatz pro Tag um {(last['adnv']/baseline['adnv']-1)*100:.1f}% und Abschlüsse pro Tag um {(last['trades']/baseline['trades']-1)*100:.1f}%. Stück je Abschluss veränderten sich von {baseline['size']:.1f} auf {last['size']:.1f}. Der gewichtete US-Anteil stieg von {baseline['share']:.4f}% auf {last['share']:.4f}%. Das Wachstum geht damit über einen bloßen Anstieg des gesamten US-Handels hinaus.",'','## Auffällige Tage und Mixwechsel','', '| Datum | Stück Mio. | USD Mio. | Abschlüsse | Tape B | Tape C | Stück/Abschluss |','|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if r['trade_date'] in ['2026-07-31','2026-08-03','2026-08-10','2026-08-12','2026-09-14',rows[-1]['trade_date']]:
            lines.append(f"| {r['trade_date']} | {number(r,'share_volume')/1e6:.2f} | {number(r,'dollar_volume')/1e6:.2f} | {number(r,'trade_count'):,.0f} | {number(r,'tape_b_volume')/number(r,'share_volume')*100:.1f}% | {number(r,'tape_c_volume')/number(r,'share_volume')*100:.1f}% | {number(r,'avg_shares_per_trade'):.1f} |")
    lines += ['','Die Spitze Ende Juli/Anfang August ist Tape-B-lastig. Tape B ist ein Listing-Universum und kein reiner ETF-Nachweis. Ein niedrigerer aggregierter USD/Stück-Wert und größere Ausführungen erklären, warum Stückzahl allein die wirtschaftliche Größe verzerrt. Einzelne Namen oder Auslöser sind aus diesen Aggregaten nicht bestimmbar.','',f"In den letzten fünf Sessions entfallen {last['tape_c']:.1f}% der Stückzahl auf Tape C. Das ist TXSE-Handel in Nasdaq-gelisteten Wertpapieren, nicht Nasdaqs eigener Ausführungsmarktanteil. Mehr kleinere Ausführungen sind mit stärker fragmentiertem Routing vereinbar; eine Zuordnung zu HFT, Retail oder institutioneller Akkumulation ist damit nicht belegt.",'','## Statistischer Anomalie-Screen','', 'Robuster z-Wert = 0,67448975 × (Beobachtung − Median der vorangehenden 20 Sessions) / MAD. Der aktuelle Tag ist von der Referenz ausgeschlossen. Schwelle: |z| > 3,5 in mindestens einer der fünf Kennzahlen. Bei weniger als 20 Vorgängern oder MAD=0 bleibt der Wert leer. Das ist ein deskriptiver Screen in einer jungen, nichtstationären Zeitreihe, kein Manipulationsnachweis.','', 'Markierte Tage: '+(', '.join(stats['flagged_dates']) or 'keine')+'. Alle Werte stehen in `data/txse_anomalies.csv`.','', '## Grenzen und nächste Messpunkte','', '- Keine Orderbuchdaten, Spreads, Stornos, Aggressorseite, Tickerdaten, Intraday-Kurve oder Brokeridentitäten enthalten. Aussagen zu Akkumulation, Spoofing, Wash Trading, HFT-Anteil oder Ausführungsqualität wären unbelegt.','- Der bisherige Feldname `lit_market_share_pct` bedeutet Börsenvolumen ohne FINRA/TRF. Börsenausführungen können nicht angezeigte Liquidität enthalten; die Variable misst keinen reinen Lit-Anteil.','- 06.–09.07. fehlen als TXSE-Beobachtungen in der abgefragten Quelle. Der Abruf beginnt am angekündigten Start 06.07.; die beobachtete Reihe beginnt am 10.07. Fehlende Werte werden nicht auf null gesetzt.','- Laufende Woche und Feiertagswochen nicht über absolute Wochensummen vergleichen. ADV und gleich lange Sessionfenster sind die zentrale Vergleichsbasis.','- Nach Listing-Wechseln: venue capture je Wertpapier, Auktionsanteil, Spread/Tiefe und Persistenz über 5/20 Sessions messen. Ein Listing-Wechsel verschiebt nicht automatisch das gesamte Sekundärmarktvolumen zur TXSE.','', '## Daten und Reproduzierbarkeit','', '`data/raw/market_history_2026.csv` enthält das vollständige abgerufene Cboe-Jahresfile einschließlich Nasdaq; Begleit-JSON enthält Abrufzeit und SHA-256. `data/txse_nasdaq_comparison.csv` enthält TXSE und NASDAQ (Q) im Beobachtungsfenster.','', '[Cboe-Datenbeschreibung](https://www.cboe.com/markets/us/equities/market-statistics/historical-market-volume) · [News und Ereigniskalender](news_2026-09-16.md)','']
    nasdaq=[r for r in peers if r['Market Participant']=='NASDAQ (Q)' and last['start']<=r['Day']<=last['end']]
    assert len(nasdaq)==5, 'Missing NASDAQ comparison sessions'
    nq_adv=sum(float(r['Total Shares']) for r in nasdaq)/5
    nq_adnv=sum(float(r['Total Notional']) for r in nasdaq)/5
    lines += ['## Größenordnung gegenüber Nasdaq (Q)', '', f"NASDAQ (Q) erreicht im gleichen 5-Session-Fenster {nq_adv/1e9:.3f} Mrd. Stück und {nq_adnv/1e9:.2f} Mrd. USD pro Tag. TXSE entspricht {last['adv']/nq_adv*100:.2f}% dieses Stückvolumens und {last['adnv']/nq_adnv*100:.2f}% dieses Dollarumsatzes. Verglichen wird die einzelne Nasdaq-Börse Q, nicht die gesamte Nasdaq-Gruppe und nicht das Listing-Universum Tape C.", '']
    Path('reports/volume_behavior.md').write_text('\n'.join(lines))
    svg=Path('reports/charts/txse_dashboard.svg').read_text();svg=svg[svg.index('<svg'):]
    body='<p>'+html.escape(lines[2])+'</p><p>'+html.escape(next(x for x in lines if x.startswith('Gegenüber')))+'</p><p>'+html.escape(next(x for x in lines if x.startswith('In den letzten')))+'</p><p><a href="https://github.com/MarcusRWDTCU/TXSE-Volume-Scraper/blob/main/reports/volume_behavior.md">Vollständige Analyse und Methodik</a> · <a href="https://github.com/MarcusRWDTCU/TXSE-Volume-Scraper/blob/main/reports/news_2026-09-16.md">News und Ereigniskalender</a></p>'
    Path('reports/txse_dashboard.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ORC | TXSE Volume Monitor</title><style>body{margin:0;background:'+BG+';color:'+INK+';font:16px/1.6 system-ui}main{max-width:1280px;margin:auto;padding:24px}svg{width:100%;height:auto}details{padding:24px;border-top:1px solid #bbb}p{overflow-wrap:anywhere}</style><main>'+svg+'<details><summary>Methodik und vollständige Auswertung</summary>'+body+'</details></main></html>')
    print(json.dumps(stats,indent=2))
if __name__=='__main__': main()
