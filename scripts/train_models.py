"""
Explora los datos, selecciona variables con RFECV, compara modelos
y guarda predicciones y gráficas.

Relación con el Diplomado:
- Análisis exploratorio de datos.
- Estadística inferencial.
- Selección de variables mediante RFECV.
- Machine Learning.
- Redes neuronales.

Se comparan tres modelos clásicos:
1. Regresión Lineal.
2. Árbol de Decisión.
3. Random Forest.

Cada modelo realiza su propia selección de variables mediante RFECV.

La validación es temporal: los datos del pasado se utilizan para
entrenar y los periodos posteriores para validar.

Entrada:
    datos/processed/observations.csv
    o datos/raw/hour.csv

Salida:
    outputs/metrics/
    outputs/predictions/
    outputs/figures/

Ejecución desde la raíz del proyecto:
    python scripts/train_models.py
"""

import json
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from scipy import stats

from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
)
from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

from common import (
    ROOT,
    RAW,
    OUTPUTS,
    FEATURE_COLUMNS,
    CATEGORICAL,
    NUMERIC,
    SelectColumns,
    load_observations,
)


warnings.filterwarnings("ignore", category=UserWarning)

RANDOM_STATE = 42

# Configuración de la selección de variables.
N_SPLITS = 5
MIN_FEATURES = 4
TUNING_ITERATIONS = 10


# ============================================================
# 1. PREPROCESAMIENTO
# ============================================================

def make_preprocessor(feature_columns=None):
    """
    Construye el preprocesador usando únicamente las columnas
    seleccionadas por RFECV.

    Las variables numéricas se imputan y escalan.
    Las variables categóricas se imputan y codifican con OneHotEncoder.
    """

    if feature_columns is None:
        feature_columns = FEATURE_COLUMNS

    numeric_columns = [
        col for col in feature_columns
        if col in NUMERIC
    ]

    categorical_columns = [
        col for col in feature_columns
        if col in CATEGORICAL
    ]

    transformers = []

    if numeric_columns:
        numeric_pipeline = Pipeline([
            (
                "impute",
                SimpleImputer(strategy="median")
            ),
            (
                "scale",
                StandardScaler()
            ),
        ])

        transformers.append(
            ("numeric", numeric_pipeline, numeric_columns)
        )

    if categorical_columns:
        categorical_pipeline = Pipeline([
            (
                "impute",
                SimpleImputer(strategy="most_frequent")
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False
                )
            ),
        ])

        transformers.append(
            ("categorical", categorical_pipeline, categorical_columns)
        )

    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=False
    )


class GroupedImportanceRegressor(BaseEstimator, RegressorMixin):
    """One-hot encodes inputs and exposes importances per source column.

    RFECV then removes whole original variables. For categorical variables,
    the importance of all one-hot levels is summed into that source variable.
    """

    def __init__(self, estimator):
        self.estimator = estimator

    def fit(self, X, y):
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        self.preprocessor_ = make_preprocessor(list(self.feature_names_in_))
        transformed = self.preprocessor_.fit_transform(X)
        self.estimator_ = clone(self.estimator).fit(transformed, y)

        if hasattr(self.estimator_, "feature_importances_"):
            raw_importance = np.asarray(self.estimator_.feature_importances_)
        elif hasattr(self.estimator_, "coef_"):
            raw_importance = np.abs(np.asarray(self.estimator_.coef_)).reshape(-1)
        else:
            raise TypeError(
                f"{type(self.estimator_).__name__} no expone importancias ni coeficientes"
            )

        transformed_names = self.preprocessor_.get_feature_names_out()
        grouped = []
        for name in self.feature_names_in_:
            if name in NUMERIC:
                mask = transformed_names == name
            else:
                mask = np.char.startswith(
                    transformed_names.astype(str), f"{name}_"
                )
            grouped.append(float(np.sum(raw_importance[mask])))
        self.feature_importances_ = np.asarray(grouped, dtype=float)
        return self

    def predict(self, X):
        transformed = self.preprocessor_.transform(X.loc[:, self.feature_names_in_])
        return self.estimator_.predict(transformed)


class GroupRFECV:
    """Temporal recursive elimination that selects whole source variables."""

    def __init__(self, estimator, cv, min_features_to_select):
        self.estimator = estimator
        self.cv = cv
        self.min_features_to_select = min_features_to_select

    def fit(self, X, y):
        columns = list(X.columns)
        scores_by_count = {count: [] for count in range(self.min_features_to_select, len(columns) + 1)}

        for train_idx, validation_idx in self.cv.split(X):
            X_fit, X_validation = X.iloc[train_idx], X.iloc[validation_idx]
            y_fit, y_validation = y.iloc[train_idx], y.iloc[validation_idx]
            selected = columns.copy()

            while len(selected) >= self.min_features_to_select:
                ranked = GroupedImportanceRegressor(self.estimator).fit(X_fit[selected], y_fit)
                prediction = ranked.predict(X_validation[selected])
                scores_by_count[len(selected)].append(
                    float(mean_squared_error(y_validation, prediction) ** 0.5)
                )
                if len(selected) == self.min_features_to_select:
                    break
                selected.pop(int(np.argmin(ranked.feature_importances_)))

        self.cv_rmse_by_feature_count_ = {
            count: float(np.mean(scores)) for count, scores in scores_by_count.items()
        }
        self.n_features_ = min(
            self.cv_rmse_by_feature_count_,
            key=lambda count: (self.cv_rmse_by_feature_count_[count], count),
        )

        selected = columns.copy()
        self.ranking_ = np.ones(len(columns), dtype=int)
        remaining_indices = list(range(len(columns)))
        rank = 2
        while len(selected) > self.n_features_:
            ranked = GroupedImportanceRegressor(self.estimator).fit(X[selected], y)
            removed_position = int(np.argmin(ranked.feature_importances_))
            removed_original_index = remaining_indices.pop(removed_position)
            self.ranking_[removed_original_index] = rank
            selected.pop(removed_position)
            rank += 1

        self.support_ = np.asarray([column in selected for column in columns], dtype=bool)
        self.estimator_ = GroupedImportanceRegressor(self.estimator).fit(X[selected], y)
        return self


# ============================================================
# 2. INTERVALO DE CONFIANZA
# ============================================================

def ci_mean(values, confidence=0.95):
    values = np.asarray(values, dtype=float)
    mean = float(np.mean(values))
    se = stats.sem(values)
    lo, hi = stats.t.interval(confidence, len(values) - 1, loc=mean, scale=se)
    return [float(lo), float(hi)]


def parameter_search_space(estimator):
    """Espacio acotado para el ajuste automático de cada modelo."""
    if isinstance(estimator, LinearRegression):
        return {"model__fit_intercept": [True, False], "model__positive": [False, True]}
    if isinstance(estimator, DecisionTreeRegressor):
        return {
            "model__max_depth": [None, 8, 12, 18, 24, 32],
            "model__min_samples_split": [2, 5, 10, 20],
            "model__min_samples_leaf": [1, 2, 5, 10],
            "model__max_features": [1.0, "sqrt", 0.7],
        }
    if isinstance(estimator, RandomForestRegressor):
        return {
            "model__n_estimators": [100, 200, 300, 500],
            "model__max_depth": [None, 12, 18, 24, 32],
            "model__min_samples_split": [2, 5, 10],
            "model__min_samples_leaf": [1, 2, 3, 5],
            "model__max_features": [1.0, "sqrt", 0.7],
        }
    raise TypeError(f"Modelo sin espacio de búsqueda: {type(estimator).__name__}")

def calculate_percentage_errors(y_true, y_pred):
    """
    Calcula MAPE y WAPE como porcentajes.

    MAPE: promedio del error porcentual absoluto. Se excluyen
    observaciones cuyo valor real sea cero, porque no se puede
    dividir entre cero.

    WAPE: suma de errores absolutos / suma de valores reales
    absolutos. Esta métrica sí aprovecha todas las observaciones.
    """

    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()

    absolute_errors = np.abs(y_true - y_pred)

    non_zero_mask = y_true != 0

    if np.any(non_zero_mask):
        mape = np.mean(
            absolute_errors[non_zero_mask]
            / np.abs(y_true[non_zero_mask])
        ) * 100
    else:
        mape = np.nan

    denominator = np.sum(np.abs(y_true))

    if denominator > 0:
        wape = (
            np.sum(absolute_errors) / denominator
        ) * 100
    else:
        wape = np.nan

    return {
        "test_mape": float(mape),
        "test_wape": float(wape),
    }


# ============================================================
# 3. SELECCIÓN DE VARIABLES CON RFECV
# ============================================================

def make_rfecv(estimator):
    """
    Construye un selector recursivo temporal por grupos de variables.

    La selección se realiza sobre las variables originales. Cada fold ajusta
    su propio one-hot encoder y las importancias de los niveles categóricos
    se agregan de vuelta a la variable fuente antes de eliminarla.

    Para la importancia de las variables:
    - Regresión Lineal: suma de coeficientes absolutos por variable.
    - Árbol de Decisión y Random Forest: suma de importancias one-hot.

    La validación interna también respeta el orden temporal.
    """

    selector = GroupRFECV(
        estimator=estimator,
        cv=TimeSeriesSplit(n_splits=N_SPLITS),
        min_features_to_select=MIN_FEATURES,
    )

    return selector


def select_features(estimator, X_train, y_train):
    """
    Ejecuta RFECV y devuelve las columnas seleccionadas.

    El selector se ajusta exclusivamente con los datos recibidos.
    """

    selector = make_rfecv(estimator)

    selector.fit(X_train, y_train)

    selected_features = [
        feature
        for feature, selected in zip(
            X_train.columns,
            selector.support_
        )
        if selected
    ]

    return selector, selected_features


# ============================================================
# 4. CONSTRUCCIÓN DEL MODELO FINAL
# ============================================================

def make_model_pipeline(estimator, selected_features):
    """
    Construye el Pipeline final.

    Primero conserva las variables seleccionadas.
    Después realiza el preprocesamiento.
    Finalmente entrena el modelo.
    """

    return Pipeline([
        (
            "select",
            SelectColumns(selected_features)
        ),
        (
            "preprocess",
            make_preprocessor(selected_features)
        ),
        (
            "model",
            clone(estimator)
        ),
    ])


# ============================================================
# 5. VALIDACIÓN CRUZADA TEMPORAL CON RFECV
# ============================================================

def evaluate_model_with_rfecv(
    name,
    estimator,
    X_train,
    y_train
):
    """
    Evalúa un modelo mediante validación temporal anidada.

    Para cada pliegue externo:
    1. RFECV selecciona variables usando el entrenamiento del pliegue.
    2. Se entrena el modelo con las variables seleccionadas.
    3. Se evalúa con el siguiente bloque temporal.

    Esto evita seleccionar variables utilizando información
    del bloque que se está evaluando.
    """

    outer_cv = TimeSeriesSplit(n_splits=N_SPLITS)

    fold_rmse = []
    fold_mae = []
    fold_r2 = []
    fold_mape = []
    fold_wape = []
    selected_by_fold = []

    print("\n" + "=" * 65)
    print(f"MODELO: {name}")
    print("=" * 65)

    for fold, (train_index, validation_index) in enumerate(
        outer_cv.split(X_train),
        start=1
    ):

        X_fold_train = X_train.iloc[train_index]
        X_fold_validation = X_train.iloc[validation_index]

        y_fold_train = y_train.iloc[train_index]
        y_fold_validation = y_train.iloc[validation_index]

        # Selección de variables únicamente con el pasado.
        selector, selected_features = select_features(
            estimator,
            X_fold_train,
            y_fold_train
        )

        selected_by_fold.append(selected_features)

        # Construcción del modelo con las variables seleccionadas.
        pipeline = make_model_pipeline(
            estimator,
            selected_features
        )
        search = RandomizedSearchCV(
            estimator=pipeline,
            param_distributions=parameter_search_space(estimator),
            n_iter=TUNING_ITERATIONS,
            scoring="neg_root_mean_squared_error",
            cv=TimeSeriesSplit(n_splits=3),
            random_state=RANDOM_STATE,
            n_jobs=1,
            refit=True,
        )
        search.fit(X_fold_train, y_fold_train)
        pipeline = search.best_estimator_

        predictions = np.clip(
            pipeline.predict(X_fold_validation),
            0,
            None
        )

        rmse = mean_squared_error(
            y_fold_validation,
            predictions
        ) ** 0.5

        mae = mean_absolute_error(
            y_fold_validation,
            predictions
        )

        r2 = r2_score(
            y_fold_validation,
            predictions
        )

        percentage_errors = calculate_percentage_errors(
            y_fold_validation,
            predictions
        )
        mape = percentage_errors["test_mape"]
        wape = percentage_errors["test_wape"]

        fold_rmse.append(float(rmse))
        fold_mae.append(float(mae))
        fold_r2.append(float(r2))
        fold_mape.append(float(mape))
        fold_wape.append(float(wape))

        print(f"\nPliegue {fold}")
        print(f"Variables seleccionadas: {selected_features}")
        print(f"Número de variables: {len(selected_features)}")
        print(f"RMSE: {rmse:.3f}")
        print(f"MAE:  {mae:.3f}")
        print(f"R²:   {r2:.4f}")
        print(f"MAPE: {mape:.2f}%")
        print(f"WAPE: {wape:.2f}%")

    return {
        "modelo": name,
        "cv_rmse_promedio": float(np.mean(fold_rmse)),
        "cv_rmse_std": float(np.std(fold_rmse, ddof=1)),
        "cv_mae_promedio": float(np.mean(fold_mae)),
        "cv_r2_promedio": float(np.mean(fold_r2)),
        "cv_mape_promedio": float(np.nanmean(fold_mape)),
        "cv_wape_promedio": float(np.nanmean(fold_wape)),
        "variables_por_pliegue": selected_by_fold,
    }


# ============================================================
# 6. ENTRENAMIENTO FINAL Y EVALUACIÓN
# ============================================================

def train_final_model(
    estimator,
    X_train,
    y_train,
    X_test,
    y_test
):
    """
    Realiza la selección final con el conjunto de entrenamiento
    y evalúa el modelo en el conjunto de prueba.
    """

    selector, selected_features = select_features(
        estimator,
        X_train,
        y_train
    )

    search = RandomizedSearchCV(
        estimator=make_model_pipeline(estimator, selected_features),
        param_distributions=parameter_search_space(estimator),
        n_iter=TUNING_ITERATIONS,
        scoring="neg_root_mean_squared_error",
        cv=TimeSeriesSplit(n_splits=N_SPLITS),
        random_state=RANDOM_STATE,
        n_jobs=1,
        refit=True,
    )
    search.fit(X_train, y_train)
    final_pipeline = search.best_estimator_
    best_params = search.best_params_

    predictions = np.clip(
        final_pipeline.predict(X_test),
        0,
        None
    )

    metrics = {
        "test_rmse": float(
            mean_squared_error(y_test, predictions) ** 0.5
        ),
        "test_mae": float(
            mean_absolute_error(y_test, predictions)
        ),
        "test_r2": float(
            r2_score(y_test, predictions)
        ),
        **calculate_percentage_errors(y_test, predictions),
        "best_params": best_params,
    }

    return (
        final_pipeline,
        selector,
        selected_features,
        predictions,
        metrics,
    )


# ============================================================
# 7. FUNCIÓN PRINCIPAL
# ============================================================

def main():

    # --------------------------------------------------------
    # Crear carpetas de salida
    # --------------------------------------------------------

    for folder in [
        OUTPUTS / "figures",
        OUTPUTS / "metrics",
        OUTPUTS / "predictions",
    ]:
        folder.mkdir(
            parents=True,
            exist_ok=True
        )

    # --------------------------------------------------------
    # Cargar datos
    # --------------------------------------------------------

    df = load_observations().dropna(
        subset=["count"]
    ).copy()

    df = df.sort_values(
        "datetime"
    ).reset_index(drop=True)

    X = df[FEATURE_COLUMNS].copy()

    y = df["count"].astype(float)

    print("\nDatos cargados correctamente.")
    print(f"Número de observaciones: {len(df)}")
    print(f"Número de variables iniciales: {len(FEATURE_COLUMNS)}")


    # --------------------------------------------------------
    # Análisis descriptivo
    # --------------------------------------------------------

    desc = df[["count", "temp", "atemp", "humidity", "windspeed"]].describe().T
    desc.to_csv(OUTPUTS / "metrics" / "estadistica_descriptiva.csv")

    work = df.loc[df.workingday == 1, "count"].to_numpy()
    nonwork = df.loc[df.workingday == 0, "count"].to_numpy()
    t_stat, p_value = stats.ttest_ind(work, nonwork, equal_var=False)
    diff = float(work.mean() - nonwork.mean())
    se_diff = np.sqrt(work.var(ddof=1) / len(work) + nonwork.var(ddof=1) / len(nonwork))
    df_welch = (work.var(ddof=1) / len(work) + nonwork.var(ddof=1) / len(nonwork)) ** 2 / (
        (work.var(ddof=1) / len(work)) ** 2 / (len(work) - 1)
        + (nonwork.var(ddof=1) / len(nonwork)) ** 2 / (len(nonwork) - 1)
    )
    ci_diff = [
        float(diff - stats.t.ppf(0.975, df_welch) * se_diff),
        float(diff + stats.t.ppf(0.975, df_welch) * se_diff),
    ]
    inference = {
        "mean_demand_per_hour": float(y.mean()),
        "mean_demand_ci95_t": ci_mean(y),
        "working_day_mean": float(work.mean()),
        "non_working_day_mean": float(nonwork.mean()),
        "difference_work_minus_nonwork": diff,
        "difference_ci95_welch": ci_diff,
        "welch_t_statistic": float(t_stat),
        "welch_p_value": float(p_value),
        "interpretation": "Asociación en estos datos; no prueba que el calendario cause la demanda.",
    }
    (OUTPUTS / "metrics" / "inferencia.json").write_text(
        json.dumps(inference, indent=2, ensure_ascii=False), encoding="utf-8"
    )


    # --------------------------------------------------------
    # División temporal: 80 % entrenamiento / 20 % prueba
    # --------------------------------------------------------

    split = int(len(df) * 0.80)

    X_train = X.iloc[:split].copy()
    X_test = X.iloc[split:].copy()

    y_train = y.iloc[:split].copy()
    y_test = y.iloc[split:].copy()

    print("\nDivisión temporal:")
    print(f"Entrenamiento: {len(X_train)} observaciones")
    print(f"Prueba:        {len(X_test)} observaciones")
    print(f"Inicio prueba: {df.datetime.iloc[split]}")
    print(f"Fin prueba:    {df.datetime.iloc[-1]}")


    # --------------------------------------------------------
    # Definir modelos
    # --------------------------------------------------------

    models = {
        "Regresión lineal": LinearRegression(),

        "Árbol de decisión": DecisionTreeRegressor(
            max_depth=18,
            min_samples_leaf=5,
            random_state=RANDOM_STATE
        ),

        "Random Forest": RandomForestRegressor(
            n_estimators=100,
            max_depth=22,
            min_samples_leaf=3,
            n_jobs=-1,
            random_state=RANDOM_STATE
        ),
    }


    # --------------------------------------------------------
    # Evaluación con RFECV independiente por modelo
    # --------------------------------------------------------

    cv_results = []

    for name, estimator in models.items():

        result = evaluate_model_with_rfecv(
            name,
            estimator,
            X_train,
            y_train
        )

        cv_results.append(result)


    # --------------------------------------------------------
    # Comparación de modelos por RMSE de validación
    # --------------------------------------------------------

    results = pd.DataFrame([
        {
            "modelo": item["modelo"],
            "cv_rmse_promedio": item["cv_rmse_promedio"],
            "cv_rmse_std": item["cv_rmse_std"],
            "cv_mae_promedio": item["cv_mae_promedio"],
            "cv_r2_promedio": item["cv_r2_promedio"],
            "cv_mape_promedio": item["cv_mape_promedio"],
            "cv_wape_promedio": item["cv_wape_promedio"],
        }
        for item in cv_results
    ])

    results = results.sort_values(
        "cv_rmse_promedio"
    ).reset_index(drop=True)

    results.to_csv(
        OUTPUTS / "metrics" / "comparacion_modelos.csv",
        index=False
    )

    print("\n" + "=" * 65)
    print("COMPARACIÓN DE MODELOS")
    print("=" * 65)

    print(
        results.to_string(index=False)
    )


    # --------------------------------------------------------
    # Entrenamiento final de cada modelo y prueba final
    # --------------------------------------------------------

    final_models = {}
    final_predictions = {}
    final_metrics = {}
    selected_variables = []

    for name, estimator in models.items():

        print("\n" + "=" * 65)
        print(f"ENTRENAMIENTO FINAL: {name}")
        print("=" * 65)

        (
            pipeline,
            selector,
            selected_features,
            predictions,
            metrics,
        ) = train_final_model(
            estimator,
            X_train,
            y_train,
            X_test,
            y_test
        )

        final_models[name] = pipeline
        final_predictions[name] = predictions
        final_metrics[name] = metrics
        if metrics["best_params"]:
            print(f"Mejores hiperparámetros: {metrics['best_params']}")

        print("\nVariables seleccionadas:")
        for feature in selected_features:
            print(f"- {feature}")

        print("\nMétricas del conjunto de prueba:")
        print(f"RMSE: {metrics['test_rmse']:.3f}")
        print(f"MAE:  {metrics['test_mae']:.3f}")
        print(f"R²:   {metrics['test_r2']:.4f}")
        print(f"MAPE: {metrics['test_mape']:.2f}%")
        print(f"WAPE: {metrics['test_wape']:.2f}%")

        for feature in selected_features:
            selected_variables.append({
                "modelo": name,
                "variable": feature,
            })


    # --------------------------------------------------------
    # Guardar variables seleccionadas
    # --------------------------------------------------------

    variables_df = pd.DataFrame(
        selected_variables
    )

    variables_df.to_csv(
        OUTPUTS / "metrics" / "variables_seleccionadas.csv",
        index=False
    )


    # --------------------------------------------------------
    # Guardar métricas finales de cada modelo
    # --------------------------------------------------------

    results["test_rmse"] = results["modelo"].map(
        lambda name: final_metrics[name]["test_rmse"]
    )

    results["test_mae"] = results["modelo"].map(
        lambda name: final_metrics[name]["test_mae"]
    )

    results["test_r2"] = results["modelo"].map(
        lambda name: final_metrics[name]["test_r2"]
    )

    results["test_mape"] = results["modelo"].map(
        lambda name: final_metrics[name]["test_mape"]
    )

    results["test_wape"] = results["modelo"].map(
        lambda name: final_metrics[name]["test_wape"]
    )
    results["best_params"] = results["modelo"].map(
        lambda name: final_metrics[name]["best_params"]
    )

    results.to_csv(
        OUTPUTS / "metrics" / "comparacion_modelos.csv",
        index=False
    )


    # --------------------------------------------------------
    # Seleccionar el mejor modelo
    # --------------------------------------------------------

    best_name = results.iloc[0]["modelo"]

    best = final_models[best_name]

    pred_best = final_predictions[best_name]

    joblib.dump(
        best,
        OUTPUTS / "metrics" / "mejor_modelo.joblib"
    )

    print("\n" + "=" * 65)
    print(f"MEJOR MODELO: {best_name}")
    print("=" * 65)


    # --------------------------------------------------------
    # Entrenamiento de red neuronal con Keras
    # --------------------------------------------------------

    nn_metrics = None
    nn_history = None

    try:

        import tensorflow as tf

        tf.keras.utils.set_random_seed(
            RANDOM_STATE
        )

        prep = make_preprocessor()

        n_fit = int(
            len(X_train) * 0.85
        )

        X_fit = prep.fit_transform(
            X_train.iloc[:n_fit]
        ).astype("float32")

        X_val = prep.transform(
            X_train.iloc[n_fit:]
        ).astype("float32")

        X_holdout = prep.transform(
            X_test
        ).astype("float32")

        y_fit = y_train.iloc[:n_fit].to_numpy(
            dtype="float32"
        )

        y_val = y_train.iloc[n_fit:].to_numpy(
            dtype="float32"
        )

        y_holdout = y_test.to_numpy(
            dtype="float32"
        )

        model = tf.keras.Sequential([
            tf.keras.layers.Input(
                shape=(X_fit.shape[1],)
            ),

            tf.keras.layers.Dense(
                64,
                activation="relu"
            ),

            tf.keras.layers.Dropout(0.15),

            tf.keras.layers.Dense(
                32,
                activation="relu"
            ),

            tf.keras.layers.Dense(1),
        ])

        model.compile(
            optimizer=tf.keras.optimizers.Adam(
                learning_rate=0.001
            ),
            loss="mse",
            metrics=["mae"]
        )

        early = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=8,
            restore_best_weights=True
        )

        hist = model.fit(
            X_fit,
            y_fit,
            validation_data=(X_val, y_val),
            epochs=200,
            batch_size=128,
            callbacks=[early],
            verbose=0
        )

        pred_nn = np.clip(
            model.predict(
                X_holdout,
                verbose=0
            ).ravel(),
            0,
            None
        )

        nn_metrics = {
            "modelo": "Red neuronal Keras",

            "test_rmse": float(
                mean_squared_error(
                    y_holdout,
                    pred_nn
                ) ** 0.5
            ),

            "test_mae": float(
                mean_absolute_error(
                    y_holdout,
                    pred_nn
                )
            ),

            "test_r2": float(
                r2_score(
                    y_holdout,
                    pred_nn
                )
            ),

            **calculate_percentage_errors(
                y_holdout,
                pred_nn
            ),

            "epocas_entrenadas": len(
                hist.history["loss"]
            ),

            "epoca_mejor_validacion": int(
                np.argmin(
                    hist.history["val_loss"]
                ) + 1
            ),
        }

        nn_history = hist.history

        model.save(
            OUTPUTS / "metrics" / "red_neuronal.keras"
        )

    except Exception as exc:

        pred_nn = np.full_like(
            pred_best,
            np.nan
        )

        nn_metrics = {
            "modelo": "Red neuronal Keras",
            "error": str(exc),
        }

        print("\nNo fue posible entrenar la red neuronal.")
        print(f"Detalle: {exc}")


    # --------------------------------------------------------
    # Guardar resultados generales
    # --------------------------------------------------------

    all_metrics = {
        "source_file": (
            "hour.csv"
            if (RAW / "hour.csv").exists()
            else "observations.csv"
        ),

        "n_observations": int(len(df)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),

        "test_start": str(
            df.datetime.iloc[split]
        ),

        "test_end": str(
            df.datetime.iloc[-1]
        ),

        "model_selection": (
            "Menor RMSE promedio en validación cruzada "
            "temporal de 5 pliegues con RFECV independiente "
            "para cada modelo."
        ),

        "best_classical_model": str(best_name),

        "classical_models": results.to_dict(
            orient="records"
        ),

        "selected_variables": {
            name: [
                feature
                for feature in FEATURE_COLUMNS
                if feature in final_models[name].named_steps["select"].columns
            ]
            for name in models
        },

        "neural_network": nn_metrics,

        "inference": inference,
    }

    (
        OUTPUTS / "metrics" / "resultados.json"
    ).write_text(
        json.dumps(
            all_metrics,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )


    # --------------------------------------------------------
    # Guardar predicciones
    # --------------------------------------------------------

    pred_df = pd.DataFrame({
        "datetime": df.datetime.iloc[split:].to_numpy(),

        "actual_demand": y_test.to_numpy(),

        "predicted_classical": pred_best,

        "predicted_neural": pred_nn,

        "model_classical": best_name,
    })

    pred_df.to_csv(
        OUTPUTS / "predictions" / "holdout_predictions.csv",
        index=False
    )

    if nn_history:
        pd.DataFrame(
            nn_history
        ).to_csv(
            OUTPUTS / "metrics" / "keras_history.csv",
            index=False
        )


    # --------------------------------------------------------
    # Tabla comparativa de los cuatro modelos en el conjunto
    # de prueba
    # --------------------------------------------------------

    metric_results = results[
        [
            "modelo",
            "test_rmse",
            "test_mae",
            "test_r2",
            "test_mape",
            "test_wape",
        ]
    ].copy()

    # Keras se agrega únicamente si terminó su entrenamiento.
    if nn_metrics is not None and "error" not in nn_metrics:
        metric_results = pd.concat(
            [
                metric_results,
                pd.DataFrame([{
                    "modelo": "Red neuronal Keras",
                    "test_rmse": nn_metrics["test_rmse"],
                    "test_mae": nn_metrics["test_mae"],
                    "test_r2": nn_metrics["test_r2"],
                    "test_mape": nn_metrics["test_mape"],
                    "test_wape": nn_metrics["test_wape"],
                }])
            ],
            ignore_index=True
        )

    metric_results.to_csv(
        OUTPUTS / "metrics" / "comparacion_modelos_prueba.csv",
        index=False
    )


    # --------------------------------------------------------
    # Figuras para el reporte, tablero y exposición
    # --------------------------------------------------------

    sns.set_theme(
        style="whitegrid"
    )

    # Demanda promedio por hora.
    hourly = df.groupby(
        "hour",
        as_index=False
    )["count"].mean()

    plt.figure(figsize=(9, 4.6))

    sns.lineplot(
        data=hourly,
        x="hour",
        y="count",
        marker="o",
        color="#177E89"
    )

    plt.title("Demanda promedio por hora")
    plt.xlabel("Hora del día")
    plt.ylabel("Alquileres por hora (promedio)")

    plt.tight_layout()

    plt.savefig(
        OUTPUTS / "figures" / "demanda_por_hora.png",
        dpi=160
    )

    plt.close()


    # Demanda promedio por temporada.
    seasonal = df.groupby(
        "season",
        as_index=False
    )["count"].mean()

    plt.figure(figsize=(7, 4.5))

    sns.barplot(
        data=seasonal,
        x="season",
        y="count",
        color="#177E89"
    )

    plt.title("Demanda promedio por temporada")
    plt.xlabel("Temporada (1 a 4)")
    plt.ylabel("Alquileres por hora (promedio)")

    plt.tight_layout()

    plt.savefig(
        OUTPUTS / "figures" / "demanda_por_temporada.png",
        dpi=160
    )

    plt.close()


    # --------------------------------------------------------
    # Comparación de RMSE en el conjunto de prueba
    # --------------------------------------------------------

    plt.figure(figsize=(9, 5))

    sns.barplot(
        data=metric_results,
        x="modelo",
        y="test_rmse"
    )

    plt.title("Comparación de modelos: RMSE en prueba")
    plt.xlabel("Modelo")
    plt.ylabel("RMSE (alquileres)")
    plt.xticks(rotation=15)
    plt.tight_layout()

    plt.savefig(
        OUTPUTS / "figures" / "comparacion_rmse.png",
        dpi=160
    )

    plt.close()


    # --------------------------------------------------------
    # Comparación de MAE en el conjunto de prueba
    # --------------------------------------------------------

    plt.figure(figsize=(9, 5))

    sns.barplot(
        data=metric_results,
        x="modelo",
        y="test_mae"
    )

    plt.title("Comparación de modelos: MAE en prueba")
    plt.xlabel("Modelo")
    plt.ylabel("MAE (alquileres)")
    plt.xticks(rotation=15)
    plt.tight_layout()

    plt.savefig(
        OUTPUTS / "figures" / "comparacion_mae.png",
        dpi=160
    )

    plt.close()


    # --------------------------------------------------------
    # Comparación de R² en el conjunto de prueba
    # --------------------------------------------------------

    plt.figure(figsize=(9, 5))

    sns.barplot(
        data=metric_results,
        x="modelo",
        y="test_r2"
    )

    plt.title("Comparación de modelos: R² en prueba")
    plt.xlabel("Modelo")
    plt.ylabel("R²")
    plt.xticks(rotation=15)
    plt.tight_layout()

    plt.savefig(
        OUTPUTS / "figures" / "comparacion_r2.png",
        dpi=160
    )

    plt.close()


    # --------------------------------------------------------
    # Comparación de MAPE en el conjunto de prueba
    # --------------------------------------------------------

    plt.figure(figsize=(9, 5))

    sns.barplot(
        data=metric_results,
        x="modelo",
        y="test_mape"
    )

    plt.title("Comparación de modelos: MAPE en prueba")
    plt.xlabel("Modelo")
    plt.ylabel("MAPE (%)")
    plt.xticks(rotation=15)
    plt.tight_layout()

    plt.savefig(
        OUTPUTS / "figures" / "comparacion_mape.png",
        dpi=160
    )

    plt.close()


    # --------------------------------------------------------
    # Comparación de WAPE en el conjunto de prueba
    # --------------------------------------------------------

    plt.figure(figsize=(9, 5))

    sns.barplot(
        data=metric_results,
        x="modelo",
        y="test_wape"
    )

    plt.title("Comparación de modelos: WAPE en prueba")
    plt.xlabel("Modelo")
    plt.ylabel("WAPE (%)")
    plt.xticks(rotation=15)
    plt.tight_layout()

    plt.savefig(
        OUTPUTS / "figures" / "comparacion_wape.png",
        dpi=160
    )

    plt.close()


    # --------------------------------------------------------
    # Comparación de RMSE de validación cruzada temporal
    # Los resultados corresponden a los tres modelos clásicos.
    # --------------------------------------------------------

    plt.figure(figsize=(9, 5))

    plt.bar(
        results["modelo"],
        results["cv_rmse_promedio"],
        yerr=results["cv_rmse_std"],
        capsize=5
    )

    plt.title("RMSE de validación cruzada temporal (RFECV)")
    plt.xlabel("Modelo clásico")
    plt.ylabel("RMSE promedio (alquileres)")
    plt.xticks(rotation=15)
    plt.tight_layout()

    plt.savefig(
        OUTPUTS / "figures" / "comparacion_rmse_validacion.png",
        dpi=160
    )

    plt.close()


    # --------------------------------------------------------
    # Demanda real vs mejor modelo clásico y Keras
    # Se muestran los primeros 168 registros (aprox. 7 días).
    # Las métricas, en cambio, utilizan todo el conjunto de prueba.
    # --------------------------------------------------------

    if nn_metrics is not None and "error" not in nn_metrics:

        n_points = min(168, len(y_test))

        comparison = pd.DataFrame({
            "datetime": df["datetime"].iloc[
                split:split + n_points
            ].to_numpy(),

            "Demanda real": y_test.iloc[:n_points].to_numpy(),

            f"Mejor modelo clásico ({best_name})": pred_best[:n_points],

            "Red neuronal Keras": pred_nn[:n_points],
        })

        comparison_long = comparison.melt(
            id_vars="datetime",
            var_name="serie",
            value_name="alquileres"
        )

        plt.figure(figsize=(14, 6))

        sns.lineplot(
            data=comparison_long,
            x="datetime",
            y="alquileres",
            hue="serie"
        )

        plt.title(
            "Demanda real vs predicciones: "
            f"{best_name} y Keras"
        )
        plt.xlabel("Fecha y hora")
        plt.ylabel("Alquileres por hora")
        plt.xticks(rotation=30)
        plt.tight_layout()

        plt.savefig(
            OUTPUTS / "figures" / "comparacion_predicciones_keras.png",
            dpi=160
        )

        plt.close()


    # --------------------------------------------------------
    # Valores observados vs estimados: mejor clásico y Keras
    # --------------------------------------------------------

    plt.figure(figsize=(7, 7))

    plt.scatter(
        y_test,
        pred_best,
        s=16,
        alpha=0.40,
        label=f"Mejor modelo clásico ({best_name})"
    )

    # Agregar Keras solo si el entrenamiento fue exitoso.
    if nn_metrics is not None and "error" not in nn_metrics:
        plt.scatter(
            y_test,
            pred_nn,
            s=16,
            alpha=0.40,
            label="Red neuronal Keras"
        )

    # Línea diagonal: representa una predicción perfecta.
    max_values = [
        float(y_test.max()),
        float(np.max(pred_best))
    ]

    if nn_metrics is not None and "error" not in nn_metrics:
        max_values.append(float(np.max(pred_nn)))

    lim = max(max_values)

    plt.plot(
        [0, lim],
        [0, lim],
        "--",
        label="Predicción perfecta"
    )

    plt.title("Demanda observada vs estimada")
    plt.xlabel("Alquileres observados")
    plt.ylabel("Alquileres estimados")
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        OUTPUTS / "figures" / "observado_vs_estimado.png",
        dpi=160
    )

    plt.close()


    # Evolución del entrenamiento de la red neuronal.
    if nn_history:

        plt.figure(figsize=(8, 4.5))

        plt.plot(
            nn_history["loss"],
            label="Entrenamiento"
        )

        plt.plot(
            nn_history["val_loss"],
            label="Validación"
        )

        plt.title(
            "Red neuronal: pérdida durante el entrenamiento"
        )

        plt.xlabel("Época")
        plt.ylabel("Error cuadrático medio")

        plt.legend()

        plt.tight_layout()

        plt.savefig(
            OUTPUTS / "figures" / "keras_early_stopping.png",
            dpi=160
        )

        plt.close()


    # --------------------------------------------------------
    # Resumen en pantalla
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("RESULTADOS FINALES")
    print("=" * 65)

    print(
        results.to_string(index=False)
    )

    print("\nMejor modelo clásico:")
    print(best_name)

    print("\nComparación en el conjunto de prueba:")
    print(metric_results.to_string(index=False))

    print("\nRed neuronal:")
    print(nn_metrics)

    print("\nVariables seleccionadas:")
    print(
        variables_df.to_string(index=False)
    )

    print(
        "\nResultados guardados en outputs/metrics, "
        "outputs/predictions y outputs/figures."
    )

    return all_metrics


if __name__ == "__main__":
    main()
