CREATE SCHEMA
IF NOT EXISTS raw;

CREATE SCHEMA
IF NOT EXISTS  staging;

CREATE SCHEMA
IF NOT EXISTS  final;

CREATE TABLE
IF NOT EXISTS raw.stock_prices_5min
(
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume NUMERIC,
    raw_data JSONB,
    PRIMARY KEY (symbol, timestamp)
);

CREATE TABLE
IF NOT EXISTS raw.stock_prices_daily
(
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume NUMERIC,
    raw_data JSONB,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE
IF NOT EXISTS staging.stock_prices_5min
(
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume NUMERIC,
    PRIMARY KEY (symbol, timestamp)
);

CREATE TABLE
IF NOT EXISTS staging.stock_prices_daily
(
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume NUMERIC,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS final.intraday_analytics (
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    high_low_spread NUMERIC GENERATED ALWAYS AS (high - low) STORED,
    price_change NUMERIC GENERATED ALWAYS AS (close - open) STORED,
    prev_close NUMERIC,
    price_change_pct NUMERIC,
    vwap NUMERIC,
    last_refreshed TIMESTAMP,
    PRIMARY KEY (symbol, timestamp)
);

CREATE TABLE IF NOT EXISTS final.daily_analytics (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    daily_range NUMERIC GENERATED ALWAYS AS (high - low) STORED,
    price_change_pct_daily NUMERIC,
    moving_avg_50d NUMERIC,
    moving_avg_200d NUMERIC,
    volume_avg_20d NUMERIC,
    rsi_14 NUMERIC,
    last_refreshed TIMESTAMP,
    PRIMARY KEY (symbol, date)
);
