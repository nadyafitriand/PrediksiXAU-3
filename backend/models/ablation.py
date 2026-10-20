import pandas as pd  # noqa: F401
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

from config import TRAIN_RATIO
from processing.clean_price_data import load_price_data
from processing.create_features import FEATURE_COLUMNS, create_features

BASE_COLS = [c for c in FEATURE_COLUMNS if c != "cpi_yoy_pct"]


def run(cols: list[str], name: str, df) -> None:
    usable = df.dropna(subset=cols + ["target_return"]).reset_index(drop=True)
    split = int(len(usable) * TRAIN_RATIO)
    tr, te = usable.iloc[:split], usable.iloc[split:]

    model = XGBRegressor(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(tr[cols], tr["target_return"])

    pred_return = model.predict(te[cols])
    pred_close = te["close"].values * (1 + pred_return)
    actual_close = te["target_close"].values

    mae = mean_absolute_error(actual_close, pred_close)
    rmse = mean_squared_error(actual_close, pred_close) ** 0.5
    dir_acc = ((pred_return > 0) == (te["target_return"].values > 0)).mean()

    print(f"{name:<26} MAE={mae:8.2f}  RMSE={rmse:8.2f}  DirAcc={dir_acc:.4f}  n_test={len(te)}")


if __name__ == "__main__":
    df = create_features(load_price_data())
    df["time_index"] = range(len(df))

    run(BASE_COLS, "tanpa CPI", df)
    run(FEATURE_COLUMNS, "dengan CPI", df)
    run(BASE_COLS + ["time_index"], "tanpa CPI + time_index", df)