INSERT INTO final.intraday_analytics (
    symbol, timestamp, open, high, low, close, volume, prev_close, price_change_pct, vwap, last_refreshed
)
SELECT
    symbol,
    timestamp,
    open_price AS open,
    high_price AS high,
    low_price AS low,
    close_price AS close,
    volume::BIGINT,
    LAG(close_price) OVER (PARTITION BY symbol ORDER BY timestamp) AS prev_close,
    ROUND(
        (
            (close_price - LAG(close_price) OVER (PARTITION BY symbol ORDER BY timestamp)) /
            NULLIF(LAG(close_price) OVER (PARTITION BY symbol ORDER BY timestamp), 0)
        ) * 100, 2
    ) AS price_change_pct,
    ROUND(
        SUM(close_price * volume) OVER (PARTITION BY symbol, DATE(timestamp)) /
        NULLIF(SUM(volume) OVER (PARTITION BY symbol, DATE(timestamp)), 0), 2
    ) AS vwap,
    CURRENT_TIMESTAMP AS last_refreshed
FROM staging.stock_prices_5min
ON CONFLICT (symbol, timestamp) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume,
    prev_close = EXCLUDED.prev_close,
    price_change_pct = EXCLUDED.price_change_pct,
    vwap = EXCLUDED.vwap,
    last_refreshed = EXCLUDED.last_refreshed
WHERE final.intraday_analytics.last_refreshed < EXCLUDED.last_refreshed;
