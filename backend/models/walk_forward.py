import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

from config import HORIZON_DAYS
from processing.clean_price_data import load_price_data
from processing.create_features import FEATURE_COLUMNS, create_features

BASE_COLS = [c for c in FEATURE_COLUMNS if c != "cpi_yoy_pct"]
N_FOLDS = 4
TEST_SIZE = 126  # sekitar 6 bulan bursa per fold


def make_model():
    return XGBRegressor(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )


def evaluate(cols, tr, te):
    model = make_model()
    model.fit(tr[cols], tr["target_return"])
    pred_return = model.predict(te[cols])
    pred_close = te["close"].values * (1 + pred_return)
    actual_close = te["target_close"].values

    mae = mean_absolute_error(actual_close, pred_close)
    rmse = mean_squared_error(actual_close, pred_close) ** 0.5
    dir_acc = ((pred_return > 0) == (te["target_return"].values > 0)).mean()
    baseline_mae = mean_absolute_error(actual_close, te["close"].values)
    return mae, rmse, dir_acc, baseline_mae


def main():
    df = create_features(load_price_data())
    df["time_index"] = range(len(df))
    rng = np.random.default_rng(42)
    df["noise"] = rng.standard_normal(len(df))

    usable = df.dropna(subset=FEATURE_COLUMNS + ["target_return", "time_index"]).reset_index(drop=True)
    n = len(usable)

    variants = {
        "tanpa CPI": BASE_COLS,
        "dengan CPI": FEATURE_COLUMNS,
        "tanpa CPI + time_index": BASE_COLS + ["time_index"],
        "tanpa CPI + noise": BASE_COLS + ["noise"],
    }
    results = {name: [] for name in variants}
    baseline_maes = []

    for k in range(N_FOLDS):
        test_end = n - k * TEST_SIZE
        test_start = test_end - TEST_SIZE
        train_end = test_start - HORIZON_DAYS  # embargo: target latih tidak boleh masuk periode uji
        tr = usable.iloc[:train_end]
        te = usable.iloc[test_start:test_end]
        period = f"{te['date'].min().date()} s.d. {te['date'].max().date()}"

        print(f"\nFold {N_FOLDS - k} | uji: {period} | n_train={len(tr)} n_test={len(te)}")
        for name, cols in variants.items():
            mae, rmse, dir_acc, base_mae = evaluate(cols, tr, te)
            results[name].append((mae, rmse, dir_acc))
            if name == "tanpa CPI":
                baseline_maes.append(base_mae)
            print(f"  {name:<24} MAE={mae:8.2f}  RMSE={rmse:8.2f}  DirAcc={dir_acc:.4f}")
        print(f"  {'baseline harga terakhir':<24} MAE={base_mae:8.2f}")

    print("\n=== Rata-rata lintas fold ===")
    for name, vals in results.items():
        arr = np.array(vals)
        print(f"{name:<24} MAE={arr[:,0].mean():8.2f}  RMSE={arr[:,1].mean():8.2f}  DirAcc={arr[:,2].mean():.4f}")
    print(f"{'baseline harga terakhir':<24} MAE={np.mean(baseline_maes):8.2f}")


if __name__ == "__main__":
    main()