# Presentación HTML

`Proyecto_DemandaBicicletas_interactiva.html` es la presentación del proyecto y se puede abrir directamente en un navegador moderno. No requiere servidor, conexión a internet ni archivos externos: incluye los datos de exploración y el modelo Random Forest de `scripts/demand_agent.py`.

La presentación tiene ocho partes: contexto, problema, requerimiento analítico, estrategia de solución, exploración de datos (con Power BI pendiente de elaboración manual), alternativas, resultados frente a una referencia simple y recomendación. Incluye filtros y gráficas exploratorias con ejes etiquetados, un esquema del holdout 80/20 y los cinco pliegues temporales, una gráfica horaria de demanda real frente a Random Forest y Keras, comparación de métricas y el predictor final ejecutable localmente.

En la diapositiva 6 se pueden modificar fecha y hora, temporada, feriado, día laboral, clima, temperatura, sensación térmica, humedad y velocidad del viento. Los valores iniciales son los solicitados para el ejemplo. La predicción se calcula dentro del navegador con el modelo serializado; los datos ingresados no se envían a un servidor. Para demostrar el LLM durante la defensa, ejecuta `python scripts/demand_agent.py --require-llm` con `OPENAI_API_KEY` y `OPENAI_MODEL` configurados.

Para regenerar la presentación después de actualizar los datos o el modelo, abre PowerShell en la raíz del repositorio y ejecuta:

```powershell
python scripts/build_interactive_html.py
```

El generador usa los artefactos de `outputs/metrics/` y `outputs/predictions/holdout_predictions.csv`, producidos por `train_models.py`; incrusta 168 horas consecutivas de demanda real y predicciones en la presentación. Después escribe `presentacion/Proyecto_DemandaBicicletas_interactiva.html`.
