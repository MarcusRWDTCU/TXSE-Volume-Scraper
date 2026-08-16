from datetime import date
from txse_scraper.history import extract

def test_extract_cboe_row_and_market_share():
    rows=[
      {"Day":"2026-08-14","Market Participant":"Texas Stock Exchange (F)","Tape A Shares":"10","Tape B Shares":"20","Tape C Shares":"30","Total Shares":"60","Tape A Notional":"100","Tape B Notional":"200","Tape C Notional":"300","Total Notional":"600","Tape A Trade Count":"1","Tape B Trade Count":"2","Tape C Trade Count":"3","Total Trade Count":"6"},
      {"Day":"2026-08-14","Market Participant":"NASDAQ (Q)","Tape A Shares":"100","Tape B Shares":"200","Tape C Shares":"300","Total Shares":"600","Tape A Notional":"1","Tape B Notional":"1","Tape C Notional":"1","Total Notional":"3","Tape A Trade Count":"1","Tape B Trade Count":"1","Tape C Trade Count":"1","Total Trade Count":"3"},
    ]
    r=extract(rows,date(2026,8,14),date(2026,8,14))[0]
    assert r["share_volume"]==60
    assert r["dollar_volume"]==600
    assert r["trade_count"]==6
    assert round(r["market_share_pct"],6)==round(60/660*100,6)
    assert r["tape_c_volume"]==30
