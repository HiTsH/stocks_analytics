-- Create schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS final;

-- Raw tables
CREATE TABLE IF NOT EXISTS raw.stock_prices_5min (
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open_price NUMERIC(10, 2) NOT NULL,
    high_price NUMERIC(10, 2) NOT NULL,
    low_price NUMERIC(10, 2) NOT NULL,
    close_price NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    raw_data JSONB,
    PRIMARY KEY (symbol, timestamp)
);

CREATE TABLE IF NOT EXISTS raw.stock_prices_daily (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open_price NUMERIC(10, 2) NOT NULL,
    high_price NUMERIC(10, 2) NOT NULL,
    low_price NUMERIC(10, 2) NOT NULL,
    close_price NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    raw_data JSONB,
    PRIMARY KEY (symbol, date)
);

-- Staging tables
CREATE TABLE IF NOT EXISTS staging.stock_prices_5min (
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open_price NUMERIC(10, 2) NOT NULL,
    high_price NUMERIC(10, 2) NOT NULL,
    low_price NUMERIC(10, 2) NOT NULL,
    close_price NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    PRIMARY KEY (symbol, timestamp)
);

CREATE TABLE IF NOT EXISTS staging.stock_prices_daily (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open_price NUMERIC(10, 2) NOT NULL,
    high_price NUMERIC(10, 2) NOT NULL,
    low_price NUMERIC(10, 2) NOT NULL,
    close_price NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    PRIMARY KEY (symbol, date)
);

-- Final analytics tables
CREATE TABLE IF NOT EXISTS final.intraday_analytics (
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open NUMERIC(10, 2) NOT NULL,
    high NUMERIC(10, 2) NOT NULL,
    low NUMERIC(10, 2) NOT NULL,
    close NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    high_low_spread NUMERIC(10, 2) GENERATED ALWAYS AS (high - low) STORED,
    price_change NUMERIC(10, 2) GENERATED ALWAYS AS (close - open) STORED,
    prev_close NUMERIC(10, 2),
    price_change_pct NUMERIC(10, 2),
    vwap NUMERIC(10, 2),
    last_refreshed TIMESTAMP,
    PRIMARY KEY (symbol, timestamp)
);

CREATE TABLE IF NOT EXISTS final.daily_analytics (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(10, 2) NOT NULL,
    high NUMERIC(10, 2) NOT NULL,
    low NUMERIC(10, 2) NOT NULL,
    close NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    daily_range NUMERIC(10, 2) GENERATED ALWAYS AS (high - low) STORED,
    price_change_pct_daily NUMERIC(10, 2),
    moving_avg_50d NUMERIC(10, 2),
    moving_avg_200d NUMERIC(10, 2),
    volume_avg_20d NUMERIC(10, 2),
    rsi_14 NUMERIC(10, 2),
    last_refreshed TIMESTAMP,
    PRIMARY KEY (symbol, date)
);
