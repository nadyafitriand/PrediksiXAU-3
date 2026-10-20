import json

import pandas as pd

from config import DATA_DIR, FORECAST_TEST_PATH, HORIZON_DAYS, METRICS_PATH, PRICE_DATA_PATH
from models.analyze_sentiment import load_sentiment_results
from models.predict_price import predict_next_month
from processing.clean_price_data import load_price_data
from services.recommendation import build_recommendation

SENTIMENT_KEYS = ["positive", "neutral", "negative"]
CPI_OUT_PATH = DATA_DIR / "cpi_us.csv"


def _try(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _price_summary() -> dict:
    df = load_price_data(PRICE_DATA_PATH)
    last, prev = df.iloc[-1], df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    change = (last["close"] - prev["close"]) / prev["close"] * 100
    return {
        "date": pd.Timestamp(last["date"]).strftime("%Y-%m-%d"),
        "close": round(float(last["close"]), 2),
        "change_1d_percent": round(float(change), 2),
        "data_rows": int(len(df)),
    }


def _macro_summary() -> dict:
    if not CPI_OUT_PATH.exists():
        raise FileNotFoundError(
            "Data CPI belum tersedia. Jalankan: python -m processing.clean_macro_data"
        )
    cpi = pd.read_csv(CPI_OUT_PATH, parse_dates=["period", "release_date"])
    as_of = pd.Timestamp(load_price_data(PRICE_DATA_PATH)["date"].max())

    released = cpi[(cpi["release_date"] <= as_of) & cpi["cpi_yoy_pct"].notna()]
    if released.empty:
        raise ValueError("Belum ada CPI yang sudah dirilis pada tanggal data harga terakhir.")

    last = released.iloc[-1]
    return {
        "as_of_date": as_of.strftime("%Y-%m-%d"),
        "period": last["period"].strftime("%Y-%m"),
        "release_date": last["release_date"].strftime("%Y-%m-%d"),
        "release_source": str(last["release_source"]),
        "cpi_index": round(float(last["cpi"]), 3),
        "cpi_yoy_percent": round(float(last["cpi_yoy_pct"]), 2),
    }


def _sentiment_summary(df: pd.DataFrame) -> dict:
    counts = df["sentiment"].value_counts()
    total = int(len(df))
    dist = {k: int(counts.get(k, 0)) for k in SENTIMENT_KEYS}
    percent = {k: round(v / total * 100, 2) if total else 0.0 for k, v in dist.items()}
    return {"total": total, "counts": dist, "percent": percent}


def get_dashboard() -> dict:
    price, price_err = _try(_price_summary)
    prediction, pred_err = _try(predict_next_month)
    sentiment_df, sent_err = _try(load_sentiment_results)
    macro, macro_err = _try(_macro_summary)
    sentiment = _sentiment_summary(sentiment_df) if sentiment_df is not None else None

    recommendation = build_recommendation(
        prediction["predicted_change_percent"] if prediction else None,
        sentiment["percent"] if sentiment else None,
    )
    messages = [m for m in [price_err, pred_err, sent_err, macro_err] if m]

    return {
        "data_status": "ready" if (price and prediction) else "not_ready",
        "messages": messages,
        "price": price,
        "prediction": prediction,
        "sentiment": sentiment,
        "macro": macro,
        "recommendation": recommendation,
    }


def get_price_history(days: int = 180) -> dict:
    try:
        df = load_price_data(PRICE_DATA_PATH).tail(days)
    except Exception as exc:  # noqa: BLE001
        return {"data_status": "not_ready", "message": str(exc), "dates": [], "closes": []}
    return {
        "data_status": "ready",
        "dates": df["date"].dt.strftime("%Y-%m-%d").tolist(),
        "closes": [round(float(x), 2) for x in df["close"]],
    }


def get_forecast() -> dict:
    prediction, pred_err = _try(predict_next_month)
    if not METRICS_PATH.exists() or not FORECAST_TEST_PATH.exists():
        return {
            "data_status": "not_ready",
            "message": "Model belum dievaluasi. Jalankan: python -m models.train_xgboost",
            "prediction": prediction,
        }

    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    test = pd.read_csv(FORECAST_TEST_PATH)
    return {
        "data_status": "ready" if prediction else "partial",
        "message": pred_err,
        "horizon_days": HORIZON_DAYS,
        "prediction": prediction,
        "metrics": metrics,
        "test_series": {
            "dates": test["date"].tolist(),
            "actual": [round(float(x), 2) for x in test["actual"]],
            "predicted": [round(float(x), 2) for x in test["predicted"]],
            "baseline": [round(float(x), 2) for x in test["baseline"]],
        },
    }


def get_sentiment() -> dict:
    df, err = _try(load_sentiment_results)
    if df is None:
        return {"data_status": "not_ready", "message": err}

    daily = (
        df.assign(day=df["date"].dt.strftime("%Y-%m-%d"))
        .groupby(["day", "sentiment"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )
    for key in SENTIMENT_KEYS:
        if key not in daily:
            daily[key] = 0

    trend = [
        {"date": day, **{k: int(row[k]) for k in SENTIMENT_KEYS}}
        for day, row in daily.iterrows()
    ]
    return {
        "data_status": "ready",
        "summary": _sentiment_summary(df),
        "trend": trend[-60:],
    }


def get_news(q: str = "", category: str = "", sentiment: str = "") -> dict:
    df, err = _try(load_sentiment_results)
    if df is None:
        return {"data_status": "not_ready", "message": err, "categories": [], "items": []}

    items = df.copy()
    if q:
        mask = (
            items["title"].astype(str).str.contains(q, case=False, na=False)
            | items["source"].astype(str).str.contains(q, case=False, na=False)
        )
        items = items[mask]
    if category:
        items = items[items["category"].astype(str).str.lower() == category.lower()]
    if sentiment:
        items = items[items["sentiment"] == sentiment.lower()]

    items = items.sort_values("date", ascending=False).head(200).copy()
    items["date"] = items["date"].dt.strftime("%Y-%m-%d")
    records = items.fillna("").to_dict(orient="records")

    categories = sorted(c for c in df["category"].dropna().astype(str).unique() if c)
    return {"data_status": "ready", "categories": categories, "items": records}