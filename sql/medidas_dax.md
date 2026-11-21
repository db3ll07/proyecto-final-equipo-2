# Medidas DAX para el modelo semántico de Fabric

Esta guía explica cómo agregar al modelo semántico los cálculos para el informe. Las expresiones son **DAX**, no SQL: no se pegan en el editor de consultas SQL del Lakehouse ni se ejecutan en una consulta de base de datos. Cada bloque de código crea una medida y debe agregarse por separado.

## Orden recomendado respecto a SQL

Después de cargar las tablas al Lakehouse, ejecuta primero las consultas de [`queries.sql`](./queries.sql) siguiendo las instrucciones de [`README.md`](./README.md). Así verificas que las tablas están disponibles y completas la parte de consultas SQL del proyecto. Después, crea el modelo semántico y agrega estas medidas DAX.

SQL no es un requisito técnico para crear las medidas: ambos trabajan con las mismas tablas y podrías agregar las medidas antes. El orden anterior se recomienda para revisar los datos antes de construir el informe.

## Antes de empezar

En el Lakehouse, confirma que las cuatro tablas estén bajo **Tables**:

- `FactDemand`
- `DimDate`
- `DimHour`
- `DimConditions`

En el modelo semántico, crea o confirma estas relaciones. Cada dimensión debe filtrar a `FactDemand` en una sola dirección:

| Columna de la dimensión (lado 1) | Columna de `FactDemand` (lado varios) |
| --- | --- |
| `DimDate[date_key]` | `FactDemand[date_key]` |
| `DimHour[hour_key]` | `FactDemand[hour_key]` |
| `DimConditions[conditions_key]` | `FactDemand[conditions_key]` |

Las claves deben ser números enteros en las dos tablas. Las relaciones permiten que un filtro de fecha, hora o condiciones afecte los cálculos de `FactDemand`.

## Cómo agregar cada medida

1. En el workspace de Fabric, abre el **modelo semántico** (no el endpoint SQL del Lakehouse) y entra a **Editar modelo** si se muestra esa opción.
2. En la lista de tablas, selecciona `FactDemand`.
3. En la barra superior, selecciona **Nueva medida** (*New measure*). Aparecerá la barra de fórmulas.
4. Copia **un bloque completo** de esta guía y pégalo en la barra de fórmulas. Si ya aparece un texto inicial como `Measure =`, reemplázalo por el bloque completo.
5. Pulsa **Enter** o el botón de confirmación. Repite desde el paso 3 para cada medida.

Si Fabric indica que no reconoce las comas que separan argumentos, reemplaza esas comas por punto y coma, según la configuración regional del modelo. No cambies las comas que formen parte de texto.

## Medidas

### Alquileres observados

Suma la demanda real en el contexto de filtros actual. Por ejemplo, al filtrar por un año, suma la demanda de ese año.

```DAX
Alquileres observados = SUM(FactDemand[actual_demand])
```

### Alquileres observados en ventana de pronóstico

Suma la demanda real solo en las filas para las que existe un pronóstico. Úsala junto a **Alquileres pronosticados** para comparar ambos totales sobre las mismas horas; no compares el pronóstico de la ventana de prueba con la demanda observada de todo el histórico.

```DAX
Alquileres observados en ventana de pronóstico =
CALCULATE(
    [Alquileres observados],
    FILTER(
        FactDemand,
        NOT ISBLANK(FactDemand[predicted_classical]) &&
        NOT ISBLANK(FactDemand[actual_demand])
    )
)
```

### Alquileres pronosticados

Suma el pronóstico clásico disponible. Las filas sin pronóstico se ignoran.

```DAX
Alquileres pronosticados = SUM(FactDemand[predicted_classical])
```

### Horas con pronóstico

Cuenta las filas que tienen pronóstico. Como `FactDemand` contiene una fila por hora, el resultado es el número de horas pronosticadas bajo los filtros actuales.

```DAX
Horas con pronóstico =
COUNTROWS(
    FILTER(
        FactDemand,
        NOT ISBLANK(FactDemand[predicted_classical])
    )
)
```

### Error absoluto medio

Calcula el promedio de la diferencia absoluta entre demanda observada y pronosticada, solo en horas donde existen ambos valores. Un resultado menor significa que, en promedio, el pronóstico estuvo más cerca de la demanda real.

```DAX
Error absoluto medio =
AVERAGEX(
    FILTER(
        FactDemand,
        NOT ISBLANK(FactDemand[predicted_classical]) &&
        NOT ISBLANK(FactDemand[actual_demand])
    ),
    ABS(FactDemand[actual_demand] - FactDemand[predicted_classical])
)
```

### Sesgo del pronóstico

Calcula la diferencia promedio **pronóstico menos demanda observada** en las horas con ambos valores. Un resultado positivo indica que el modelo pronosticó de más; uno negativo, que pronosticó de menos.

```DAX
Sesgo del pronóstico =
AVERAGEX(
    FILTER(
        FactDemand,
        NOT ISBLANK(FactDemand[predicted_classical]) &&
        NOT ISBLANK(FactDemand[actual_demand])
    ),
    FactDemand[predicted_classical] - FactDemand[actual_demand]
)
```

### Demanda pico

Devuelve el mayor total observado entre las horas del día que estén incluidas en los filtros. Devuelve el **valor** de demanda máxima, no la etiqueta de la hora.

```DAX
Demanda pico =
MAXX(
    VALUES(DimHour[hour_label]),
    [Alquileres observados]
)
```

### Cambio vs hora anterior

Resta la demanda de la hora anterior a la demanda de la hora actual. Úsala en un visual que tenga una sola hora en su contexto, por ejemplo, un gráfico por `DimHour[hour_label]`. Para las 00:00 no hay hora anterior en esta dimensión y la medida queda vacía. Los filtros de fecha y condiciones se mantienen.

```DAX
Cambio vs hora anterior =
VAR HoraActual = SELECTEDVALUE(DimHour[hour_key])
VAR DemandaAnterior =
    CALCULATE(
        [Alquileres observados],
        REMOVEFILTERS(DimHour),
        DimHour[hour_key] = HoraActual - 1
    )
RETURN
IF(
    ISBLANK(HoraActual) || HoraActual = 0 || ISBLANK(DemandaAnterior),
    BLANK(),
    [Alquileres observados] - DemandaAnterior
)
```

## Usar las medidas en un informe

Después de agregar las medidas, crea un informe desde el modelo semántico. Por ejemplo:

- **Tarjetas:** `Alquileres observados`, `Alquileres pronosticados`, `Error absoluto medio` y `Horas con pronóstico`.
- **Comparación de totales:** usa `Alquileres observados en ventana de pronóstico` y `Alquileres pronosticados` para que ambos correspondan a las horas evaluadas.
- **Gráfico de líneas para comparar el pronóstico:** coloca `DimHour[hour_label]` en el eje y agrega `Alquileres observados en ventana de pronóstico` y `Alquileres pronosticados` como valores. Así ambas líneas corresponden a las mismas horas evaluadas.
- **Filtros:** agrega campos de fecha, franja horaria y condiciones desde las tablas de dimensión.

La ventana de prueba debe quedar identificada en el informe: los pronósticos solo existen para las filas que tienen un valor en `predicted_classical`.
