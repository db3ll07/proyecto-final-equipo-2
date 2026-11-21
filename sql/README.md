# Consultas SQL del proyecto

Este directorio contiene consultas de ejemplo para explorar las tablas del proyecto. `queries.sql` contiene cuatro consultas **SQL** listas para copiar y ejecutar, una por una. No son medidas DAX.

## Antes de ejecutar las consultas

Primero, confirma que el Lakehouse ya tenga estas tablas:

- `FactDemand`
- `DimDate`
- `DimHour`
- `DimConditions`

El archivo `schema.sql` describe la estructura lógica de las tablas; no es una consulta analítica y no necesitas pegarlo en Fabric. En el proyecto, `python scripts/build_sqlite.py` genera las tablas y crea `datos/processed/demand_bikes.sqlite` para ejecutarlas localmente.

## Ejecutarlas en Microsoft Fabric

1. Abre el workspace y entra al Lakehouse que contiene las tablas.
2. Abre su **endpoint de análisis SQL** (*SQL analytics endpoint*), no el editor de notebooks ni el editor de medidas DAX.
3. Selecciona **Nueva consulta SQL** (*New SQL query*).
4. Abre `queries.sql` en el proyecto, copia una consulta completa —desde su `SELECT` hasta el `;`— y pégala en el editor de Fabric.
5. Selecciona **Ejecutar** (*Run*). Revisa la cuadrícula de resultados.
6. Repite con las otras consultas, una por vez.

Si Fabric no encuentra una tabla, vuelve al Lakehouse y confirma que aparece bajo **Tables**. Los archivos que solo estén bajo **Files** todavía no son tablas consultables.

## Ejecutarlas localmente

Si prefieres usar la base SQLite del proyecto, abre `datos/processed/demand_bikes.sqlite` con una aplicación compatible con SQLite, por ejemplo DB Browser for SQLite. Abre la pestaña de consultas SQL, copia una consulta completa de `queries.sql`, ejecútala y revisa sus resultados.

## Qué responde cada consulta

1. Compara la demanda media por hora entre días laborales y no laborales.
2. Compara por mes la demanda observada y pronosticada en las mismas horas de la ventana de prueba.
3. Resume la demanda media y el número de observaciones por clima y franja horaria.
4. Calcula el error absoluto medio del pronóstico clásico para cada hora del día.

## Orden recomendado: SQL y luego DAX

Para documentar la parte SQL de la rúbrica y revisar que las tablas devuelven resultados, ejecuta primero las consultas de `queries.sql`, después de cargar las tablas al Lakehouse. Luego crea o abre el modelo semántico y agrega las medidas DAX indicadas en [`medidas_dax.md`](./medidas_dax.md).

Este orden es una recomendación de trabajo, no una dependencia técnica: SQL y DAX consultan las mismas tablas, así que las medidas DAX podrían crearse antes. No obstante, ejecutar primero SQL ayuda a comprobar que las tablas están disponibles antes de continuar con el modelo semántico.
