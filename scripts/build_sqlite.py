"""Crea tablas del proyecto en SQLite y CSV para Power BI.

Relación con el Diplomado: organización y análisis de datos. Practico SQL,
agregaciones y el modelo estrella que después se usa en una herramienta BI.
La tabla de hechos guarda cada hora; las dimensiones ayudan a filtrar por
fecha, hora y condiciones. No calcula pronósticos nuevos.

Entrada: datos/processed/observations.csv y, si existe, predicciones guardadas.
Salida: una base SQLite, tablas CSV y un resumen mensual por hora.
Ejecutar desde la raíz: python scripts/build_sqlite.py
"""
from pathlib import Path
import sqlite3
import pandas as pd
from common import ROOT, PROCESSED, OUTPUTS, load_observations


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    df = load_observations().copy()
    predictions = OUTPUTS / "predictions" / "holdout_predictions.csv"
    if predictions.exists():
        pred = pd.read_csv(predictions, parse_dates=["datetime"])
        df = df.merge(pred[["datetime", "predicted_classical", "predicted_neural"]], on="datetime", how="left")
    else:
        df["predicted_classical"] = float("nan")
        df["predicted_neural"] = float("nan")
    date = pd.to_datetime(df.datetime)
    df["date_key"] = date.dt.strftime("%Y%m%d").astype(int)
    df["hour_key"] = date.dt.hour
    condition_cols = ["weather", "temp", "atemp", "humidity", "windspeed"]
    conditions = df[condition_cols].drop_duplicates().sort_values(condition_cols).reset_index(drop=True)
    conditions.insert(0, "conditions_key", range(1, len(conditions) + 1))
    df = df.merge(conditions, on=condition_cols, how="left")
    dim_date = pd.DataFrame({"date_key": df.date_key.unique()})
    dim_date["date"] = pd.to_datetime(dim_date.date_key.astype(str), format="%Y%m%d")
    dim_date["year"] = dim_date.date.dt.year
    dim_date["month"] = dim_date.date.dt.month
    dim_date["month_name"] = dim_date.date.dt.month_name()
    dim_date["day"] = dim_date.date.dt.day
    dim_date["day_of_week"] = dim_date.date.dt.day_of_week
    dim_date["day_name"] = dim_date.date.dt.day_name()
    dim_date["is_holiday"] = df.groupby("date_key").holiday.first().reindex(dim_date.date_key).to_numpy()
    dim_date["is_working_day"] = df.groupby("date_key").workingday.first().reindex(dim_date.date_key).to_numpy()
    dim_hour = pd.DataFrame({"hour_key": range(24)})
    dim_hour["hour_label"] = dim_hour.hour_key.map(lambda h: f"{h:02d}:00")
    dim_hour["time_band"] = pd.cut(dim_hour.hour_key, [-1, 5, 11, 16, 20, 23],
                                    labels=["Madrugada", "Mañana", "Mediodía", "Tarde", "Noche"]).astype(str)
    fact = df[["datetime", "date_key", "hour_key", "conditions_key", "season", "workingday", "holiday",
               "count", "predicted_classical", "predicted_neural"]].copy()
    fact = fact.rename(columns={"count": "actual_demand"})
    fact["observation_key"] = range(1, len(fact) + 1)
    fact["actual_demand"] = fact.actual_demand.astype("Int64")
    # Guardo cada tabla como CSV para poder cargarla fácilmente en Power BI.
    tables = {"FactDemand": fact, "DimDate": dim_date, "DimHour": dim_hour,
              "DimConditions": conditions}
    for name, table in tables.items():
        table.to_csv(PROCESSED / f"{name}.csv", index=False)
    db_path = PROCESSED / "demand_bikes.sqlite"
    with sqlite3.connect(db_path) as conn:
        for name, table in tables.items():
            table.to_sql(name, conn, if_exists="replace", index=False)
        conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_fact_date ON FactDemand(date_key);
        CREATE INDEX IF NOT EXISTS idx_fact_hour ON FactDemand(hour_key);
        CREATE INDEX IF NOT EXISTS idx_fact_conditions ON FactDemand(conditions_key);
        """)
        sample = pd.read_sql_query("""
            SELECT d.year, d.month, h.hour_key, AVG(f.actual_demand) AS avg_demand,
                   AVG(f.predicted_classical) AS avg_forecast
            FROM FactDemand f
            JOIN DimDate d ON f.date_key = d.date_key
            JOIN DimHour h ON f.hour_key = h.hour_key
            GROUP BY d.year, d.month, h.hour_key ORDER BY d.year, d.month, h.hour_key
        """, conn)
    sample.to_csv(PROCESSED / "sql_month_hour_summary.csv", index=False)
    print(f"SQLite: {db_path.relative_to(ROOT)}")
    print("Tablas CSV listas para Power BI en datos/processed/")


if __name__ == "__main__":
    main()

