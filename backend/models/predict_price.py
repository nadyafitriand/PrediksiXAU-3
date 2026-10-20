import pandas as pd
from xgboost import XGBRegressor

from config import HORIZON_DAYS, MODEL_PATH, PRICE_DATA_PATH
from processing.clean_price_data import load_price_data
from processing.create_features import FEATURE_COLUMNS, create_features

_model = None


def load_model() -> XGBRegressor:
    global _model
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Model XGBoost belum dilatih. Jalankan: python -m models.train_xgboost"
        )
    if _model is None:
        model = XGBRegressor()
        model.load_model(str(MODEL_PATH))
        _model = model
    return _model


def predict_next_month() -> dict:
    model = load_model()
    df = load_price_data(PRICE_DATA_PATH)
    feat = create_features(df)

    latest = feat.dropna(subset=FEATURE_COLUMNS).iloc[[-1]]
    if latest.empty:
        raise ValueError("Data belum cukup untuk membentuk fitur prediksi.")

    pred_return = float(model.predict(latest[FEATURE_COLUMNS])[0])
    current_price = float(latest["close"].iloc[0])
    predicted_price = current_price * (1 + pred_return)
    as_of = pd.Timestamp(latest["date"].iloc[0])
    target_date = as_of + pd.offsets.BDay(HORIZON_DAYS)

    return {
        "as_of_date": as_of.strftime("%Y-%m-%d"),
        "target_date": target_date.strftime("%Y-%m-%d"),
        "horizon_trading_days": HORIZON_DAYS,
        "current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "predicted_change_percent": round(pred_return * 100, 2),
    }