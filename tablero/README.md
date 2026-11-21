# Crear el informe y las tarjetas en Microsoft Fabric

Esta guía parte de que las tablas ya están cargadas en el Lakehouse y de que el modelo semántico y las medidas DAX ya se crearon. Si todavía no has llegado a ese punto, sigue primero el orden de trabajo indicado en la [guía de consultas SQL](../sql/README.md) y crea las medidas como explica [medidas_dax.md](../sql/medidas_dax.md).

## 1. Crear un informe desde el modelo semántico

1. En Fabric, abre el **workspace** donde está tu modelo semántico.
2. Busca el modelo semántico que creaste. En su menú **…**, elige **Nuevo informe** (*New report*). Si ya abriste el modelo, también puedes usar el botón **Nuevo informe** de la barra superior.
3. Si Fabric pregunta qué datos usar, selecciona el modelo semántico de este proyecto.
4. Se abrirá un lienzo de informe en blanco. Ahí agregarás una tarjeta por cada medida.

## 2. Agregar una tarjeta

Una tarjeta muestra un solo número grande, por ejemplo el error medio del pronóstico.

1. Haz clic en un espacio vacío del lienzo.
2. En el panel **Visualizaciones** (*Visualizations*), selecciona el visual **Tarjeta** (*Card*). Si aparecen varias opciones, elige la tarjeta sencilla, no la tarjeta de varias filas.
3. En el panel **Datos** (*Data*), despliega la tabla `FactDemand` y localiza la medida que quieras mostrar. Las medidas suelen tener un icono de calculadora.
4. Arrastra la medida al recuadro **Valores** (*Values* o *Data*) del panel de visualización. También puedes marcar la casilla de la medida mientras la tarjeta está seleccionada, si tu interfaz la agrega automáticamente.
5. Para agregar otra tarjeta, haz clic en un espacio vacío del lienzo y repite estos pasos. Cambia el título de cada una para que se entienda qué representa.

Si no encuentras una medida, comprueba que la agregaste al modelo semántico. No arrastres una columna como `actual_demand` cuando quieres mostrar una de estas medidas: busca el nombre de la medida y su icono de calculadora.

## 3. Tarjetas recomendadas

Agrega una tarjeta para cada medida:

| Medida | Título sugerido | Qué representa |
| --- | --- | --- |
| `Alquileres observados en ventana de pronóstico` | Alquileres reales (periodo evaluado) | Total real en las horas para las que se generó un pronóstico. |
| `Alquileres pronosticados` | Alquileres pronosticados | Total pronosticado en esas mismas horas. |
| `Error absoluto medio` | Error medio por hora | Cuánto se alejó el pronóstico de la demanda real en promedio; un valor menor es mejor. |
| `Sesgo del pronóstico` | Sesgo medio por hora | Diferencia promedio entre pronóstico y valor real. Positivo significa que se pronosticó de más; negativo, de menos. |
| `Horas con pronóstico` | Horas evaluadas | Número de horas incluidas en la evaluación. Esta tarjeta es opcional. |

Para comparar los totales real y pronosticado, usa **Alquileres observados en ventana de pronóstico**, no `Alquileres observados`: esta última puede incluir todo el histórico, mientras que los pronósticos solo cubren el periodo de prueba.

## 4. Dar formato a una tarjeta

Repite estos pasos para cada tarjeta:

1. Selecciona la tarjeta haciendo clic en ella.
2. Abre **Formato visual** (*Format visual*, icono de brocha o rodillo) en el panel de visualizaciones.
3. En **General → Título** (*General → Title*), activa el título y escribe el título sugerido de la tabla anterior.
4. En las opciones del valor principal —pueden llamarse **Valor destacado** (*Callout value*) o **Etiqueta de datos** (*Data label*)— configura las unidades de visualización como **Ninguna** (*None*) para que Fabric no convierta los totales a miles o millones.
5. Para los alquileres, muestra 0 decimales. Para el error medio y el sesgo, puedes mostrar 1 o 2 decimales.

Los nombres de algunas opciones cambian según la versión de la interfaz. Si no encuentras una opción, selecciona primero la tarjeta y revisa el panel de formato de ese visual.

## 5. Guardar y revisar

1. Guarda el informe desde la barra superior y asígnale un nombre, por ejemplo `Demanda de bicicletas`.
2. Comprueba que las dos tarjetas de totales usen el mismo periodo de prueba.
3. Comprueba que el error absoluto medio no sea negativo. El sesgo sí puede ser positivo o negativo.
4. Como siguiente paso, agrega filtros de fecha, clima o franja horaria usando campos de las tablas de dimensión (`DimDate`, `DimConditions` y `DimHour`).

## Diseño sugerido

Una página titulada **¿Cuándo conviene redistribuir bicicletas?** puede tener las cuatro tarjetas principales en la parte superior, una línea de alquileres observados frente a pronosticados por hora y gráficos por temporada o día laboral. Identifica claramente la ventana histórica de prueba. El conjunto de datos no incluye inventario ni ubicación por estación, así que los resultados sirven como señal de planeación agregada, no como una instrucción sobre qué bicicleta mover o a dónde.
