import json

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

from config import (
    ARTIFACT_DIR,
    FORECAST_TEST_PATH,
    HORIZON_DAYS,
    METRICS_PATH,
    MODEL_PATH,
    PRICE_DATA_PATH,
    TRAIN_RATIO,
)
from processing.clean_price_data import load_price_data
from processing.create_features import FEATURE_COLUMNS, create_features


def _metrics(actual, predicted) -> dict:
    mae = mean_absolute_error(actual, predicted)
    rmse = mean_squared_error(actual, predicted) ** 0.5
    return {"MAE": round(float(mae), 4), "RMSE": round(float(rmse), 4)}


def train() -> dict:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_price_data(PRICE_DATA_PATH)
    feat = create_features(df)
    usable = feat.dropna(subset=FEATURE_COLUMNS + ["target_return"]).reset_index(drop=True)

    if len(usable) < 100:
        raise ValueError(f"Data terlalu sedikit untuk pelatihan: {len(usable)} baris.")

    split = int(len(usable) * TRAIN_RATIO)
    train_df = usable.iloc[:split]
    test_df = usable.iloc[split:]

    model = XGBRegressor(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(train_df[FEATURE_COLUMNS], train_df["target_return"])

    pred_return = model.predict(test_df[FEATURE_COLUMNS])
    actual_close = test_df["target_close"].values
    pred_close = test_df["close"].values * (1 + pred_return)
    baseline_close = test_df["close"].values

    actual_return = test_df["target_return"].values
    directional_accuracy = float(((pred_return > 0) == (actual_return > 0)).mean())
    always_up_accuracy = float((actual_return > 0).mean())

    model.save_model(str(MODEL_PATH))

    forecast = pd.DataFrame({
        "date": test_df["date"].dt.strftime("%Y-%m-%d").values,
        "actual": actual_close,
        "predicted": pred_close,
        "baseline": baseline_close,
    })
    forecast.to_csv(FORECAST_TEST_PATH, index=False)

    report = {
        "horizon_days": HORIZON_DAYS,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "train_start": train_df["date"].min().strftime("%Y-%m-%d"),
        "train_end": train_df["date"].max().strftime("%Y-%m-%d"),
        "test_start": test_df["date"].min().strftime("%Y-%m-%d"),
        "test_end": test_df["date"].max().strftime("%Y-%m-%d"),
        "model": _metrics(actual_close, pred_close),
        "baseline_last_price": _metrics(actual_close, baseline_close),
        "directional_accuracy": round(directional_accuracy, 4),
        "directional_accuracy_always_up": round(always_up_accuracy, 4),
    }
    METRICS_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = train()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nModel disimpan di: {MODEL_PATH}")