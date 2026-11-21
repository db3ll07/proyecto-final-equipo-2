"""Prepara un Excel con una hoja por tabla para cargarlo en Power BI.

Relación con el Diplomado: analítica de datos y comunicación de resultados.
El Excel conecta el trabajo de preparación/SQL con la visualización del tablero.
No crea el archivo PBIX por sí solo: deja las tablas listas para importarse.

Antes debe ejecutarse scripts/build_sqlite.py.
Comando desde la raíz: python scripts/export_powerbi_source.py
"""
from pathlib import Path
import pandas as pd
from common import ROOT, PROCESSED


def main():
    tables = ["FactDemand", "DimDate", "DimHour", "DimConditions"]
    output = PROCESSED / "powerbi_source.xlsx"
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for table in tables:
            path = PROCESSED / f"{table}.csv"
            if not path.exists():
                raise FileNotFoundError(f"No existe {path.relative_to(ROOT)}; ejecuta scripts/build_sqlite.py")
            pd.read_csv(path).to_excel(writer, sheet_name=table, index=False)
    print(f"Fuente de Power BI lista: {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

