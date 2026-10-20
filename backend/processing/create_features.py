import pandas as pd

from config import HORIZON_DAYS
from processing.clean_macro_data import add_macro_features

FEATURE_COLUMNS = [
    "return_1d",
    "return_3d",
    "return_5d",
    "return_10d",
    "return_21d",
    "return_lag_1",
    "return_lag_2",
    "return_lag_5",
    "ma_ratio_5",
    "ma_ratio_10",
    "ma_ratio_21",
    "ma_ratio_50",
    "volatility_10d",
    "volatility_21d",
    "cpi_yoy_pct",
]


def create_features(df: pd.DataFrame, horizon: int = HORIZON_DAYS) -> pd.DataFrame:
    """
    Membuat fitur dari data historis. Semua fitur hanya memakai data
    sampai tanggal acuan (tidak ada kebocoran data masa depan).
    Target: perubahan harga close setelah `horizon` baris ke depan.
    """
    d = df.copy()
    c = d["close"]
    r = c.pct_change()

    d["return_1d"] = r
    d["return_3d"] = c.pct_change(3)
    d["return_5d"] = c.pct_change(5)
    d["return_10d"] = c.pct_change(10)
    d["return_21d"] = c.pct_change(21)
    d["return_lag_1"] = r.shift(1)
    d["return_lag_2"] = r.shift(2)
    d["return_lag_5"] = r.shift(5)

    for w in [5, 10, 21, 50]:
        d[f"ma_ratio_{w}"] = c / c.rolling(w).mean() - 1

    d["volatility_10d"] = r.rolling(10).std()
    d["volatility_21d"] = r.rolling(21).std()

    d["target_close"] = c.shift(-horizon)
    d["target_return"] = d["target_close"] / c - 1

    d = add_macro_features(d)
    return d