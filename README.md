# Pronóstico de demanda de bicicletas

Proyecto final del **Diplomado Liderazgo en la Era de la IA**. El objetivo es estimar el total de alquileres de bicicletas por hora para apoyar la planeación de revisiones operativas. El modelo usa fecha, hora y condiciones meteorológicas. Se excluyen `casual` y `registered` porque suman directamente el objetivo `count` y causarían fuga de información.

## Fuente de datos

Se utiliza el **Bike Sharing Dataset** del [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/275/bike-sharing-dataset). El archivo horario `hour.csv` contiene 17,379 observaciones de Washington, D. C., entre 2011 y 2012. UCI publica el conjunto bajo licencia [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); la atribución del artículo identifica a Hadi Fanaee-T y el DOI del conjunto de datos. El script de descarga guarda el archivo en `datos/raw/`; los datos originales se excluyen de Git.

## Requisitos

- Windows 10/11, PowerShell y Python 3.11 de 64 bits.
- Conexión a internet para descargar el conjunto de datos y las dependencias.
- Espacio para instalar TensorFlow y las demás bibliotecas indicadas en `requirements.txt`.

## Ejecutar el flujo de análisis desde una clonación limpia

Abre PowerShell en la carpeta raíz del repositorio. Ejecuta los comandos en orden. Cada script guarda sus archivos dentro del repositorio usando rutas relativas, por lo que no tienes que editar rutas de tu computadora.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python scripts/download_data.py
python scripts/prepare_data.py
python scripts/train_models.py
python scripts/build_interactive_html.py
python scripts/build_sqlite.py
python scripts/export_powerbi_source.py
python scripts/generate_report_assets.py
python scripts/demand_agent.py
```

Cada ejecución de `train_models.py` ajusta automáticamente los hiperparámetros de los tres modelos mediante búsqueda aleatoria y validación temporal. El script prueba 10 combinaciones por modelo; este proceso puede tardar más, especialmente para Random Forest. Los mejores parámetros quedan en `outputs/metrics/comparacion_modelos.csv`.

Si PowerShell impide activar el entorno virtual, ejecuta esta instrucción solo para la ventana actual y vuelve a activar el entorno:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

El agente permite una demostración local sin credenciales. Para una defensa con una llamada real al LLM y a la herramienta de pronóstico, configura `OPENAI_API_KEY` y `OPENAI_MODEL` y ejecuta `python scripts/demand_agent.py --require-llm`; esta opción se detiene con error si no obtiene respuesta del LLM.

### Archivos que genera el flujo

- `datos/raw/hour.csv`: datos originales descargados desde UCI.
- `datos/processed/observations.csv`: observaciones normalizadas para el proyecto.
- `outputs/metrics/`: comparación de modelos, estadísticas y modelos entrenados.
- `outputs/predictions/`: predicciones del periodo de prueba reservado.
- `outputs/figures/`: gráficas para el reporte y la exposición.
- `datos/processed/demand_bikes.sqlite` y los CSV asociados: tablas para consultas y análisis BI.
- `datos/processed/powerbi_source.xlsx`: libro con las cuatro tablas para importar en Power BI.
- `reportes/Articulo_DemandaBicicletas.md` y `reportes/Reporte_DemandaBicicletas.pdf`: reporte actualizado con las métricas calculadas.

## Consultas SQL y Microsoft Fabric

Para preparar los datos de SQL y BI, ejecuta los scripts en este orden desde la raíz del proyecto:

1. `python scripts/download_data.py`: descarga los datos originales.
2. `python scripts/prepare_data.py`: prepara las observaciones.
3. `python scripts/train_models.py`: entrena los tres modelos clásicos y Keras, y guarda las predicciones de prueba.
4. `python scripts/build_interactive_html.py`: regenera la presentación con los resultados actuales y las gráficas comparativas.
5. `python scripts/build_sqlite.py`: crea `datos/processed/demand_bikes.sqlite` y los cuatro CSV del modelo (`FactDemand.csv`, `DimDate.csv`, `DimHour.csv` y `DimConditions.csv`).
6. En Fabric, crea un Lakehouse, carga esos cuatro CSV y conviértelos en tablas. Después ejecuta, una por una, las consultas de [`sql/queries.sql`](./sql/queries.sql) en el endpoint de análisis SQL del Lakehouse.
7. Crea el modelo semántico a partir de las tablas, configura sus relaciones y agrega las medidas de [`sql/medidas_dax.md`](./sql/medidas_dax.md).
8. Crea las tarjetas y el resto del informe siguiendo [`tablero/README.md`](./tablero/README.md).

El orden de SQL antes de DAX es recomendado para verificar las tablas y documentar las consultas de SQL; no es una dependencia técnica. Los pasos detallados están en [`sql/README.md`](./sql/README.md).

`python scripts/export_powerbi_source.py` es opcional: después de `build_sqlite.py`, genera `datos/processed/powerbi_source.xlsx` para importar las tablas en Power BI Desktop. Para el flujo de Fabric descrito arriba, se usan directamente los cuatro CSV; no hace falta cargar `demand_bikes.sqlite` ni el Excel. El repositorio no incluye un informe `.pbix` terminado.

La presentación del proyecto es [`presentacion/Proyecto_DemandaBicicletas_interactiva.html`](presentacion/Proyecto_DemandaBicicletas_interactiva.html). Es un único archivo autónomo: se abre directamente en el navegador, funciona sin servidor ni conexión a internet e incluye el modelo Random Forest para ejecutar predicciones localmente. Para regenerarla después de actualizar datos o modelo, ejecuta `python scripts/build_interactive_html.py` desde la raíz del proyecto. La diapositiva de Power BI queda pendiente para elaboración manual.

## Proyecto y rúbrica

El proyecto documenta el problema de negocio, origen y preparación de datos, análisis exploratorio, inferencia estadística, comparación de modelos, evaluación temporal, uso de SQL/BI, componente de IA generativa, conclusiones, limitaciones y referencias. El reporte corto y la presentación sirven como productos de comunicación de resultados. `docs/guia_scripts.md` explica cada etapa con lenguaje sencillo y relaciona el código con los temas del Diplomado.

### Estado frente a la rúbrica (21 de noviembre de 2026)

- **Problema y valor de negocio:** el modelo apoya una decisión concreta —cuándo revisar la disponibilidad agregada— y explica cualitativamente el costo de subestimar o sobrestimar. No hay datos de costos monetarios ni inventario, por lo que no se promete un ahorro financiero ni una recomendación por estación.
- **Datos y análisis:** se cita UCI y se documentan limpieza, exploración e inferencia. La serie tiene 17,379 filas y 165 horas sin registro dentro del intervalo continuo esperado; los huecos no se interpretan como demanda cero. El reporte generado documenta esta limitación.
- **Machine Learning:** Regresión Lineal, Árbol de Decisión y Random Forest se comparan con cinco pliegues de validación temporal y métricas de regresión, incluido RMSE y R². K-Means, PCA y DBSCAN no se aplican porque el objetivo es pronóstico supervisado y no se ha identificado una pregunta de agrupamiento o reducción dimensional que mejore la decisión.
- **Red neuronal e IA generativa:** Keras usa validación temporal interna y parada temprana; se compara con el mejor modelo clásico en el mismo holdout final. No participa en los mismos cinco pliegues, así que la comparación no demuestra superioridad de generalización. El agente de IA generativa está implementado con una herramienta real de pronóstico; para demostrar esa modalidad en la defensa se debe presentar una ejecución con `--require-llm` y respuesta real del LLM.
- **SQL y Power BI:** el script crea SQLite y los cuatro CSV requeridos, y el exportador genera un Excel para Power BI Desktop. El informe Power BI final y su inserción en la presentación siguen pendientes de elaboración manual; esta parte se completará cuando estén listos esos archivos.
- **Reporte, referencias y ejecución:** existen reporte Markdown/PDF, presentación HTML, referencias APA y un flujo documentado desde descarga hasta entregables. Antes de la entrega final, hay que completar manualmente Power BI, validar la ejecución real del agente generativo y volver a auditar los artefactos resultantes.

### Decisión y métricas

La decisión que se busca apoyar es cuándo conviene revisar la disponibilidad agregada de bicicletas. Los modelos clásicos usan RFECV con codificación one-hot dentro de cada fold y validación cruzada temporal de cinco pliegues. El último 20% cronológico se reserva como prueba final. Se reportan RMSE, MAE, MAPE, WAPE y R². Una red densa de Keras se evalúa en ese mismo periodo, con una validación temporal interna para detener el entrenamiento; no se incluyó en la misma validación cruzada de cinco pliegues que los modelos clásicos. Por ello, su resultado en el holdout común no prueba por sí solo una mejor generalización.

Los resultados son históricos y corresponden a Washington, D. C. El dataset no incluye inventario ni ubicaciones por estación. Por ello, las estimaciones son una señal de planeación y no indican cuántas bicicletas mover ni a qué lugar. La diferencia entre días laborales y no laborales es asociativa y no demuestra causalidad.

## Contenido del repositorio

- `datos/raw/`: conjunto original descargado; excluido de Git.
- `datos/processed/`: observaciones limpias, tablas SQL/BI y libro de Power BI.
- `notebooks/`: análisis exploratorio y comparación de modelos.
- `scripts/`: descarga, preparación, entrenamiento y generación de entregables.
- `sql/`: esquema, consultas y medidas DAX de ejemplo.
- `tablero/`: guía de armado del tablero en Power BI.
- `outputs/`: métricas, predicciones y figuras generadas.
- `reportes/`: artículo en Markdown y PDF.
- `presentacion/`: exposición final en HTML autónomo y su guía.
- `docs/guia_scripts.md`: instrucciones de ejecución, explicación de scripts y glosario.
- `docs/ia_generativa.md`: instrucciones y límites del asistente de IA generativa.
- `app/`: reservado; actualmente no se desarrolla una aplicación.

## Solución de problemas

- Si falta `hour.csv`, vuelve a ejecutar `python scripts/download_data.py` y verifica tu conexión a internet.
- Si aparece `ModuleNotFoundError`, activa `.venv` e instala de nuevo con `python -m pip install -r requirements.txt`.
- Si un paso indica que falta un archivo procesado, ejecuta los scripts anteriores en el orden indicado.
- Si TensorFlow no está disponible, reinstala las dependencias con Python 3.11 de 64 bits. El script informa el estado de la red neuronal junto con los resultados de los modelos clásicos.
- No borres los archivos de `outputs/metrics/` antes de ejecutar `build_sqlite.py`, porque ahí se encuentra el modelo que usa el asistente.
