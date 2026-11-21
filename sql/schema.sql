-- Esquema estrella del proyecto. El script build_sqlite.py genera estas tablas.
CREATE TABLE DimDate (
    date_key INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    is_holiday INTEGER NOT NULL,
    is_working_day INTEGER NOT NULL
);

CREATE TABLE DimHour (
    hour_key INTEGER PRIMARY KEY,
    hour_label TEXT NOT NULL,
    time_band TEXT NOT NULL
);

CREATE TABLE DimConditions (
    conditions_key INTEGER PRIMARY KEY,
    weather INTEGER NOT NULL,
    temp REAL NOT NULL,
    atemp REAL NOT NULL,
    humidity REAL NOT NULL,
    windspeed REAL NOT NULL
);

CREATE TABLE FactDemand (
    observation_key INTEGER PRIMARY KEY,
    datetime TEXT NOT NULL,
    date_key INTEGER NOT NULL REFERENCES DimDate(date_key),
    hour_key INTEGER NOT NULL REFERENCES DimHour(hour_key),
    conditions_key INTEGER NOT NULL REFERENCES DimConditions(conditions_key),
    season INTEGER NOT NULL,
    workingday INTEGER NOT NULL,
    holiday INTEGER NOT NULL,
    actual_demand INTEGER,
    predicted_classical REAL,
    predicted_neural REAL
);

