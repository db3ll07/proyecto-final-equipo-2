"""
Funciones compartidas para preparar y cargar los datos de UCI.

Relación con el Diplomado: limpieza, transformación y preparación de datos
para Machine Learning. Aquí convierto el archivo original a columnas fáciles
de usar en el resto del proyecto.

Este archivo se importa desde otros scripts; no se ejecuta directamente.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.base import BaseEstimator, TransformerMixin


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datos" / "raw"
PROCESSED = ROOT / "datos" / "processed"
OUTPUTS = ROOT / "outputs"


FEATURE_COLUMNS = [
    "season",
    "holiday",
    "workingday",
    "weather",
    "temp",
    "atemp",
    "humidity",
    "windspeed",
    "hour",
    "dayofweek",
    "month",
    "year",
]


CATEGORICAL = [
    "season",
    "holiday",
    "workingday",
    "weather",
    "hour",
    "dayofweek",
    "month",
    "year",
]


NUMERIC = [
    "temp",
    "atemp",
    "humidity",
    "windspeed",
]


class SelectColumns(BaseEstimator, TransformerMixin):
    """
    Conserva únicamente las columnas seleccionadas por RFECV.

    Se utiliza dentro del Pipeline final para asegurar que el modelo
    reciba las mismas variables que fueron seleccionadas durante
    el entrenamiento.
    """

    def __init__(self, columns):
        self.columns = columns

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X.loc[:, self.columns]

    def get_feature_names_out(self, input_features=None):
        return np.asarray(self.columns, dtype=object)


def load_observations() -> pd.DataFrame:
    """
    Carga los datos limpios o prepara la fuente original si hace falta.
    """

    processed_file = PROCESSED / "observations.csv"

    if processed_file.exists():
        df = pd.read_csv(
            processed_file,
            parse_dates=["datetime"]
        )

    else:
        source_file = RAW / "hour.csv"

        if not source_file.exists():
            raise FileNotFoundError(
                "No se encontró datos/raw/hour.csv. "
                "Ejecuta python scripts/download_data.py"
            )

        df = _uci_to_common(pd.read_csv(source_file))

    df = df.drop_duplicates(subset=["datetime"])

    df = df.sort_values("datetime").reset_index(drop=True)

    df["datetime"] = pd.to_datetime(df["datetime"])

    return add_time_features(df)


def _uci_to_common(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renombra columnas y convierte las unidades de temperatura y humedad.
    """

    return pd.DataFrame({
        "datetime": (
            pd.to_datetime(df["dteday"])
            + pd.to_timedelta(df["hr"], unit="h")
        ),

        "season": df["season"],
        "holiday": df["holiday"],
        "workingday": df["workingday"],
        "weather": df["weathersit"],

        "temp": df["temp"] * 47 - 8,
        "atemp": df["atemp"] * 66 - 16,
        "humidity": df["hum"] * 100,
        "windspeed": df["windspeed"] * 67,

        "count": df["cnt"],
    })


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega hora, día de semana, mes y año a partir de la fecha.
    """

    result = df.copy()

    date = pd.to_datetime(result["datetime"])

    result["hour"] = date.dt.hour
    result["dayofweek"] = date.dt.dayofweek
    result["month"] = date.dt.month
    result["year"] = date.dt.year

    if "count" in result:
        result["count"] = pd.to_numeric(
            result["count"],
            errors="coerce"
        )

    return result