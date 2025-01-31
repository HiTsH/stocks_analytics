INSERT INTO final.daily_analytics (
    symbol, date, open, high, low, close, volume, price_change_pct_daily, moving_avg_50d, moving_avg_200d, volume_avg_20d, last_refreshed
)
SELECT
    symbol,
    date,
    open_price AS open,
    high_price AS high,
    low_price AS low,
    close_price AS close,
    volume::BIGINT,
    ROUND(
        (
            (close_price - LAG(close_price) OVER (PARTITION BY symbol ORDER BY date)) /
            NULLIF(LAG(close_price) OVER (PARTITION BY symbol ORDER BY date), 0)
        ) * 100, 2
    ) AS price_change_pct_daily,
    ROUND(
        AVG(close_price) OVER (
            PARTITION BY symbol 
            ORDER BY date 
            ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
        ), 2
    ) AS moving_avg_50d,
    ROUND(
        AVG(close_price) OVER (
            PARTITION BY symbol 
            ORDER BY date 
            ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
        ), 2
    ) AS moving_avg_200d,
    ROUND(
        AVG(volume) OVER (
            PARTITION BY symbol 
            ORDER BY date 
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ), 2
    ) AS volume_avg_20d,
    CURRENT_TIMESTAMP AS last_refreshed
FROM staging.stock_prices_daily
ON CONFLICT (symbol, date) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume,
    price_change_pct_daily = EXCLUDED.price_change_pct_daily,
    moving_avg_50d = EXCLUDED.moving_avg_50d,
    moving_avg_200d = EXCLUDED.moving_avg_200d,
    volume_avg_20d = EXCLUDED.volume_avg_20d,
    last_refreshed = EXCLUDED.last_refreshed
WHERE final.daily_analytics.last_refreshed < EXCLUDED.last_refreshed;
