from txse_scraper.diagnostics import anomalies


def test_anomaly_uses_only_prior_sessions_and_requires_full_window():
    keys=['share_volume','dollar_volume','trade_count','market_share_pct','avg_shares_per_trade']
    rows=[dict(trade_date=f'day-{i}',**{k:str(100+i%5) for k in keys}) for i in range(20)]
    rows.append(dict(trade_date='spike',**{k:'1000' for k in keys}))
    result=anomalies(rows)
    assert not any(r['flag'] for r in result[:20])
    assert result[-1]['flag']
    assert result[-1]['share_volume_robust_z']>100
    changed=rows+[dict(trade_date='future',**{k:'1000000' for k in keys})]
    assert anomalies(changed)[:21]==result
