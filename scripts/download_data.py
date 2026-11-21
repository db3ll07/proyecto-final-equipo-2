"""Descarga el dataset horario público desde UCI.

Fuente de datos: UCI Machine Learning Repository, Bike Sharing Dataset.

Relación con el Diplomado: prepara la materia prima del proyecto. En el flujo
de datos esto corresponde a adquisición de datos antes de la limpieza y el
análisis. Se ejecuta desde la raíz con: python scripts/download_data.py
"""
from pathlib import Path
import io
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "datos" / "raw"
URL = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "hour.csv"
    if target.exists() and target.stat().st_size > 100_000:
        print(f"Ya existe {target.relative_to(ROOT)} ({target.stat().st_size:,} bytes).")
        return
    print("Descargando el archivo original de UCI...")
    with urllib.request.urlopen(URL, timeout=60) as response:
        archive = response.read()
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        payload = zf.read("hour.csv")
    target.write_bytes(payload)
    print(f"Listo: {target.relative_to(ROOT)} ({len(payload):,} bytes).")


if __name__ == "__main__":
    main()

