-- Ejecuta cada consulta por separado. Estas consultas son SQL, no medidas DAX.

-- 1. Compara la demanda media por hora entre días laborales y no laborales.
--    En DimDate, is_working_day vale 1 para día laboral y 0 para no laboral.
SELECT
    h.hour_label,
    d.is_working_day,
    AVG(f.actual_demand) AS avg_hourly_demand
FROM FactDemand AS f
JOIN DimHour AS h ON f.hour_key = h.hour_key
JOIN DimDate AS d ON f.date_key = d.date_key
GROUP BY h.hour_label, d.is_working_day
ORDER BY h.hour_label, d.is_working_day;

-- 2. Compara totales observados y pronosticados por mes.
--    Ambos totales usan solo las horas con pronóstico y demanda observada.
SELECT
    d.year,
    d.month,
    SUM(
        CASE
            WHEN f.predicted_classical IS NOT NULL
             AND f.actual_demand IS NOT NULL
            THEN f.actual_demand
        END
    ) AS actual_rentals_in_forecast_window,
    SUM(
        CASE
            WHEN f.predicted_classical IS NOT NULL
             AND f.actual_demand IS NOT NULL
            THEN f.predicted_classical
        END
    ) AS forecast_rentals_in_same_window
FROM FactDemand AS f
JOIN DimDate AS d ON f.date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 3. Muestra demanda media y cantidad de observaciones por clima y franja horaria.
SELECT
    c.weather,
    h.time_band,
    AVG(f.actual_demand) AS avg_hourly_demand,
    COUNT(f.actual_demand) AS observations_with_actual_demand
FROM FactDemand AS f
JOIN DimConditions AS c ON f.conditions_key = c.conditions_key
JOIN DimHour AS h ON f.hour_key = h.hour_key
GROUP BY c.weather, h.time_band
ORDER BY c.weather, h.time_band;

-- 4. Calcula el error absoluto medio del pronóstico clásico para cada hora del día.
--    Solo incluye filas que tienen demanda observada y pronóstico.
SELECT
    h.hour_label,
    AVG(ABS(f.actual_demand - f.predicted_classical)) AS mean_absolute_error
FROM FactDemand AS f
JOIN DimHour AS h ON f.hour_key = h.hour_key
WHERE f.predicted_classical IS NOT NULL
  AND f.actual_demand IS NOT NULL
GROUP BY h.hour_label
ORDER BY h.hour_label;
