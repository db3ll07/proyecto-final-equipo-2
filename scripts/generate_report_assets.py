"""Genera el artículo corto en Markdown y su versión PDF.

Relación con el Diplomado: comunicación de resultados, interpretación de
métricas y documentación de un proyecto de IA. El artículo lee los resultados
que produjo train_models.py; si se vuelven a entrenar modelos, se puede volver
a generar para actualizar cifras y gráficas.

Entrada: outputs/metrics/resultados.json y figuras de outputs/figures/.
Salida: reportes/Articulo_DemandaBicicletas.md y Reporte_DemandaBicicletas.pdf.
Desde la raíz: python scripts/generate_report_assets.py
"""
from pathlib import Path
import json
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reportes"
OUT = ROOT / "outputs"

REFERENCES = [
    "Fanaee-T, H., & Gama, J. (2014). Event labeling combining ensemble detectors and background knowledge. Progress in Artificial Intelligence, 2, 113–127. https://doi.org/10.1007/s13748-013-0040-3",
    "Hong, J., Han, E., & Park, D. (2024). Framework for hourly demand forecasting of bike-sharing stations: Case study of the four main gate areas in Seoul. International Journal of Urban Sciences, 28(4), 735–750. https://doi.org/10.1080/12265934.2024.2317198",
    "Feng, J., Liu, H., Zhou, J., & Zhou, Y. (2024). A spatial-temporal aggregated graph neural network for docked bike-sharing demand forecasting. ACM Transactions on Knowledge Discovery from Data, 18(9), Article 232. https://doi.org/10.1145/3690388",
    "Mehdizadeh Dastjerdi, A., & Morency, C. (2022). Bike-sharing demand prediction at community level under COVID-19 using deep learning. Sensors, 22(3), Article 1060. https://doi.org/10.3390/s22031060",
    "Fanaee-T, H. (2013). Bike Sharing [Data set]. UCI Machine Learning Repository. https://doi.org/10.24432/C5W894",
]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_report():
    REPORTS.mkdir(parents=True, exist_ok=True)
    metrics = load_json(OUT / "metrics" / "resultados.json")
    observations = pd.read_csv(ROOT / "datos" / "processed" / "observations.csv", parse_dates=["datetime"])
    expected_hours = pd.date_range(observations["datetime"].min(), observations["datetime"].max(), freq="h")
    missing_hours = len(expected_hours.difference(pd.DatetimeIndex(observations["datetime"])))
    inf = metrics["inference"]
    rows = metrics["classical_models"]
    nn = metrics["neural_network"]
    best = next(row for row in rows if row["modelo"] == metrics["best_classical_model"])
    ci = inf["mean_demand_ci95_t"]
    diff_ci = inf["difference_ci95_welch"]
    abstract = (
        "El proyecto estima el volumen total de alquileres de bicicletas por hora para apoyar la planeación de una operación de micromovilidad. "
        "Se analizaron 17,379 registros horarios del Bike Sharing Dataset de Washington D. C. (2011–2012), obtenido del UCI Machine Learning Repository. "
        "Se excluyeron los conteos casuales y registrados porque son componentes directos del objetivo. Se derivaron hora, día de semana, mes y año; se compararon regresión lineal, árbol de decisión y Random Forest con validación cruzada temporal de cinco pliegues. "
        f"Random Forest obtuvo el menor RMSE medio de validación ({best['cv_rmse_promedio']:.1f} alquileres). En el último 20% cronológico, su RMSE fue {best['test_rmse']:.1f} y R² {best['test_r2']:.3f}. "
        f"Una red densa de Keras, con parada temprana, alcanzó RMSE {nn.get('test_rmse', float('nan')):.1f} y R² {nn.get('test_r2', float('nan')):.3f} en el mismo periodo. "
        "La red obtuvo menor error en ese holdout compartido, pero no participó en los mismos cinco pliegues temporales; esta diferencia impide concluir que generalice mejor. "
        "Se recomienda usar el pronóstico como apoyo para revisar turnos y redistribución, sin extrapolarlo a estaciones individuales ni a otras ciudades."
    )
    sections = [
        ("1. Introducción y definición del problema", """
La operación de un sistema de bicicletas compartidas debe anticipar horas de demanda alta para programar revisiones y redistribuciones. La decisión que se apoya aquí es cuándo conviene revisar la disponibilidad agregada de bicicletas. La unidad de análisis es una hora para todo el sistema; no hay identificadores de estación ni inventario disponible. Por tanto, el proyecto no recomienda cuántas bicicletas mover ni a qué lugar.

El costo de equivocarse es operativo: una subestimación puede dejar menos bicicletas disponibles durante horas concurridas; una sobrestimación puede provocar movimientos de flota innecesarios. El dataset no contiene costos monetarios ni restricciones de capacidad, así que estos costos se describen de forma cualitativa y no se inventa un retorno financiero.
"""),
        ("2. Estado del arte", """
La investigación sobre bicicletas compartidas ha usado variables temporales y meteorológicas para predecir demanda y orientar la operación. Fanaee-T y Gama (2014) describen el uso de conocimiento de dominio para etiquetar eventos en datos de alquileres; su trabajo está ligado al conjunto público usado aquí. Hong et al. (2024) estudian pronósticos horarios con estaciones de bicicletas y Random Forest, y resaltan la relevancia de señales temporales y meteorológicas. Feng et al. (2024) desarrollan una red neuronal espaciotemporal para pronosticar demanda de alquileres y devoluciones por estación. Mehdizadeh Dastjerdi y Morency (2022) analizan demanda a nivel de comunidad con aprendizaje profundo.

Estos estudios incluyen señales espaciales o secuencias de inventario que el dataset de este proyecto no ofrece. Por eso se utilizan como contexto metodológico, no como una comparación directa de resultados. Para un proyecto inicial se eligen modelos tabulares sencillos y una red densa, que permiten comparar métodos de forma comprensible sin afirmar que resuelven la asignación por estación.
"""),
        ("3. Datos y análisis exploratorio", f"""
La fuente es el Bike Sharing Dataset del UCI Machine Learning Repository, atribuido a Fanaee-T (2013) y disponible bajo licencia CC BY 4.0. Contiene {metrics['n_observations']:,} filas horarias del 1 de enero de 2011 al 31 de diciembre de 2012. Se cambiaron nombres de columnas y unidades para facilitar el análisis, se combinaron fecha y hora, y se eliminaron duplicados por fecha/hora. Las filas observadas no tienen valores faltantes en las variables seleccionadas; sin embargo, faltan {missing_hours:,} marcas horarias respecto a la secuencia continua esperada. Esos huecos se conservan como ausencia de registro y no se convierten en demanda cero. La evaluación usa un corte cronológico: el último 20% de las observaciones queda reservado para la prueba final.

Las variables predictoras son temporada, feriado, día laboral, categoría meteorológica, temperatura, sensación térmica, humedad, velocidad de viento y características derivadas de fecha/hora. El objetivo `count` representa alquileres totales. Se excluyen `casual` y `registered` porque suman directamente el objetivo y filtrarían la respuesta hacia los predictores.

La demanda media observada fue {inf['mean_demand_per_hour']:.1f} alquileres por hora (IC 95%: {ci[0]:.1f}–{ci[1]:.1f}). La media en días laborales fue {inf['working_day_mean']:.1f}; en días no laborales, {inf['non_working_day_mean']:.1f}. La diferencia laboral menos no laboral fue {inf['difference_work_minus_nonwork']:.1f} (IC 95% de Welch: {diff_ci[0]:.1f}–{diff_ci[1]:.1f}; p = {inf['welch_p_value']:.3g}). Es una asociación descriptiva; el contraste no identifica un efecto causal.
"""),
        ("4. Metodología", f"""
Se ordenaron las observaciones por fecha y se reservaron los últimos {metrics['n_test']:,} registros ({metrics['n_test']/metrics['n_observations']:.0%}) como prueba temporal, desde {metrics['test_start'][:10]} hasta {metrics['test_end'][:10]}. Los modelos clásicos se ajustaron y compararon en el primer 80% con validación cruzada de cinco pliegues tipo ventana expansiva (TimeSeriesSplit). Durante la eliminación recursiva, cada fold ajusta su propio codificador one-hot; las importancias de las categorías se agrupan por variable original y la selección conserva o elimina la variable completa. Las variables numéricas se imputan y estandarizan dentro del pipeline.

Se compararon regresión lineal, árbol de decisión y Random Forest con búsqueda automática de hiperparámetros. El criterio de selección fue el menor RMSE medio de validación cruzada. Se reportan RMSE, MAE, MAPE, WAPE y R². MAPE excluye objetivos reales iguales a cero; WAPE usa el error absoluto total respecto a la demanda total.

La red Keras tuvo capas densas de 64 y 32 unidades, activación ReLU y dropout de 0.15. Se usó una partición temporal interna para validación y EarlyStopping con restauración de los mejores pesos. La comparación en la prueba utiliza el mismo último 20% cronológico. El componente generativo es un agente con prompt acotado y herramienta de pronóstico; requiere clave y modelo LLM configurados para la llamada externa, y ofrece un respaldo local ilustrativo.
"""),
        ("5. Resultados", f"""
Random Forest fue el mejor modelo clásico por RMSE medio de validación cruzada. En la prueba temporal compartida, la red neuronal obtuvo un RMSE menor que Random Forest. La red usó una validación temporal interna para detener el entrenamiento, pero no participó en los mismos cinco pliegues; por eso, el holdout común no demuestra que generalice mejor. El seguimiento recomendado es incluir la red en la misma validación temporal de cinco pliegues si se amplía el proyecto.

La tabla siguiente reúne los resultados solicitados por la rúbrica. Los valores corresponden a esta división temporal y no deben interpretarse como garantías de desempeño en otro periodo o ciudad.
"""),
        ("6. Retos, límites y conclusión", """
El conjunto es histórico (2011–2012), agregado a nivel del sistema y localizado en Washington D. C. No incluye inventario, estaciones, eventos locales ni costos. La evaluación temporal es más realista que una partición aleatoria, pero las condiciones de operación y clima pueden cambiar; el modelo no se probó en datos recientes. Las predicciones negativas se recortan a cero. El componente generativo no debe inventar estaciones ni capacidad y su respuesta requiere revisión humana.

Se recomienda usar el modelo como una señal para planear revisiones horarias, registrar predicción y demanda observada y medir errores por periodo. Antes de desplegarlo, convendría validar con datos actuales de la empresa, incluir inventario por estación y establecer el costo de faltantes frente a redistribuciones innecesarias. El resultado principal es que las variables temporales y meteorológicas permiten una predicción útil en la prueba histórica, pero no bastan para optimizar movimientos concretos.
"""),
    ]

    md = ["# Pronóstico de demanda de bicicletas por hora\n", "\n**Proyecto final — Diplomado Liderazgo en la Era de la IA**\n\n", "**Autoría:** Equipo 2 - Daniel Bello Romero\n\n", "## Resumen\n\n", abstract, "\n"]
    for title, body in sections:
        md += [f"\n## {title}\n\n", body.strip(), "\n"]
    md += ["\n### Tabla de comparación de modelos\n\n",
           "| Modelo | RMSE CV (media ± DE) | RMSE prueba | MAE prueba | MAPE prueba | WAPE prueba | R² prueba |\n|---|---:|---:|---:|---:|---:|---:|\n"]
    for row in rows:
        md.append(f"| {row['modelo']} | {row['cv_rmse_promedio']:.2f} ± {row['cv_rmse_std']:.2f} | {row['test_rmse']:.2f} | {row['test_mae']:.2f} | {row['test_mape']:.2f}% | {row['test_wape']:.2f}% | {row['test_r2']:.3f} |\n")
    md.append(f"| Red neuronal Keras | — | {nn.get('test_rmse', float('nan')):.2f} | {nn.get('test_mae', float('nan')):.2f} | {nn.get('test_mape', float('nan')):.2f}% | {nn.get('test_wape', float('nan')):.2f}% | {nn.get('test_r2', float('nan')):.3f} |\n")
    md += ["\n## Tablero Power BI y preparación SQL\n\n",
           "El repositorio crea una base SQLite y CSV para cargar: FactDemand, DimDate, DimHour y DimConditions. El esquema estrella, uniones y medidas DAX están documentados en `sql/` y `tablero/`. El tablero final debe mostrar observado y pronosticado por hora/mes, MAE, sesgo y segmentación por clima y calendario.\n",
           "\n## Anexo: componente generativo\n\n",
           "El prompt de sistema y sus ejemplos están en `docs/ia_generativa.md`. La herramienta `predict_hour_demand` consulta el modelo clásico serializado; el LLM resume el pronóstico sin inventar estaciones o inventario. Para una demostración real en la defensa, ejecuta `python scripts/demand_agent.py --require-llm` con `OPENAI_API_KEY` y `OPENAI_MODEL` configurados.\n",
           "\n## Referencias (APA 7)\n\n"]
    md.extend([f"- {ref}\n" for ref in REFERENCES])
    md_path = REPORTS / "Articulo_DemandaBicicletas.md"
    md_path.write_text("".join(md), encoding="utf-8")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#124E5A"), spaceAfter=10))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#124E5A"), spaceBefore=10, spaceAfter=5))
    styles.add(ParagraphStyle(name="BodySpanish", parent=styles["BodyText"], leading=14, spaceAfter=7, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="Reference", parent=styles["BodyText"], fontSize=8.5, leading=11, leftIndent=12, firstLineIndent=-12, spaceAfter=4))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    story = [Paragraph("Pronóstico de demanda de bicicletas por hora", styles["TitleCenter"]),
             Paragraph("Proyecto final · Diplomado Liderazgo en la Era de la IA", styles["Heading3"]),
             Paragraph("Autoría: Equipo 2 - Daniel Bello Romero · Fuente: UCI Machine Learning Repository", styles["BodyText"]),
             Spacer(1, 8), Paragraph("Resumen", styles["Section"]), Paragraph(escape(abstract), styles["BodySpanish"])]
    for title, body in sections:
        story += [Paragraph(escape(title), styles["Section"])]
        for para in body.strip().split("\n\n"):
            story.append(Paragraph(escape(para.strip()).replace("`", ""), styles["BodySpanish"]))
        if title.startswith("3."):
            for img_name, caption in [("demanda_por_hora.png", "Figura 1. Demanda promedio por hora."),
                                      ("demanda_por_temporada.png", "Figura 2. Demanda promedio por temporada.")]:
                imgpath = OUT / "figures" / img_name
                if imgpath.exists():
                    story += [Image(str(imgpath), width=5.5*inch, height=2.8*inch), Paragraph(caption, styles["Small"])]
        if title.startswith("5."):
            data = [["Modelo", "RMSE CV", "DE CV", "RMSE prueba", "MAE", "MAPE", "WAPE", "R²"]]
            data += [[r["modelo"], f"{r['cv_rmse_promedio']:.1f}", f"{r['cv_rmse_std']:.1f}", f"{r['test_rmse']:.1f}", f"{r['test_mae']:.1f}", f"{r['test_mape']:.1f}%", f"{r['test_wape']:.1f}%", f"{r['test_r2']:.3f}"] for r in rows]
            data += [["Red neuronal Keras", "—", "—", f"{nn.get('test_rmse', float('nan')):.1f}", f"{nn.get('test_mae', float('nan')):.1f}", f"{nn.get('test_mape', float('nan')):.1f}%", f"{nn.get('test_wape', float('nan')):.1f}%", f"{nn.get('test_r2', float('nan')):.3f}"]]
            table = Table(data, repeatRows=1, colWidths=[1.45*inch, .75*inch, .55*inch, .82*inch, .62*inch, .65*inch, .65*inch, .5*inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#124E5A")), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
                ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#B8C7C9")),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EFF5F5")]),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 5),
                ("RIGHTPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ]))
            story += [Spacer(1, 5), table, Spacer(1, 8)]
        if title.startswith("6."):
            for img_name, caption in [("observado_vs_estimado.png", "Figura 3. Valores observados y predichos en el periodo de prueba."),
                                      ("keras_early_stopping.png", "Figura 4. Pérdida de entrenamiento y validación de Keras.")]:
                imgpath = OUT / "figures" / img_name
                if imgpath.exists():
                    story += [Image(str(imgpath), width=4.8*inch, height=2.8*inch), Paragraph(caption, styles["Small"])]
    story.append(Paragraph("Anexo de IA generativa", styles["Section"]))
    story.append(Paragraph("Prompt, ejemplos y límites: docs/ia_generativa.md. La llamada de LLM requiere OPENAI_API_KEY y OPENAI_MODEL; el pipeline estadístico no depende de esas credenciales.", styles["BodySpanish"]))
    story.append(Paragraph("Referencias (APA 7)", styles["Section"]))
    story.extend(Paragraph(escape(ref), styles["Reference"]) for ref in REFERENCES)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#B8C7C9"))
        canvas.line(.65*inch, .55*inch, 7.85*inch, .55*inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#53666A"))
        canvas.drawString(.68*inch, .36*inch, "Proyecto final · Demanda de bicicletas")
        canvas.drawRightString(7.82*inch, .36*inch, f"Página {doc.page}")
        canvas.restoreState()

    pdf_path = REPORTS / "Equipo2_Reporte.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, rightMargin=.68*inch, leftMargin=.68*inch,
                            topMargin=.68*inch, bottomMargin=.75*inch, title="Pronóstico de demanda de bicicletas")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"Generados: {md_path.relative_to(ROOT)} y {pdf_path.relative_to(ROOT)}")


if __name__ == "__main__":
    build_report()

