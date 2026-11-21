"""Prepara una tabla limpia desde el archivo horario original de UCI.

Relación con el Diplomado: preparación de datos para Machine Learning. Practico
leer un CSV, corregir nombres y unidades, ordenar las observaciones y guardar
una tabla que los siguientes scripts pueden reutilizar.

Entrada: datos/raw/hour.csv.
Salida: datos/processed/observations.csv.
Desde la raíz: python scripts/prepare_data.py
"""
import pandas as pd
from common import ROOT, RAW, PROCESSED, _uci_to_common


def main():
    source_file = RAW / "hour.csv"
    if not source_file.exists():
        raise FileNotFoundError(
            "No se encontró datos/raw/hour.csv. Ejecuta python scripts/download_data.py"
        )

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df = _uci_to_common(pd.read_csv(source_file))
    df = df.drop_duplicates(subset=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    output_file = PROCESSED / "observations.csv"
    df.to_csv(output_file, index=False)

    print("Fuente: UCI Machine Learning Repository — Bike Sharing Dataset")
    print(f"Observaciones: {len(df):,}; columnas: {len(df.columns)}")
    print(f"Rango: {df.datetime.min()} a {df.datetime.max()}")
    print(f"Archivo procesado: {output_file.relative_to(ROOT)}")


if __name__ == "__main__":
    main()