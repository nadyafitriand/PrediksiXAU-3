from pathlib import Path

import pandas as pd

from config import DATA_DIR

CPI_RAW_PATH = DATA_DIR / "cpi_raw.csv"
CPI_RELEASE_PATH = DATA_DIR / "cpi_release_dates.csv"
CPI_OUT_PATH = DATA_DIR / "cpi_us.csv"

FALLBACK_RELEASE_DAY = 20  # estimasi konservatif jika tanggal resmi belum diisi


def load_cpi_raw(path: Path = CPI_RAW_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File CPI tidak ditemukan: {path}")

    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    date_col = "observation_date" if "observation_date" in df.columns else "date"
    if date_col not in df.columns or "cpiaucsl" not in df.columns:
        raise ValueError(f"Kolom tidak dikenali: {list(df.columns)}")

    out = pd.DataFrame({
        "period": pd.to_datetime(df[date_col], errors="coerce"),
        "cpi": pd.to_numeric(df["cpiaucsl"], errors="coerce"),
    })
    return out.dropna().sort_values("period").reset_index(drop=True)


def build_release_dates(cpi: pd.DataFrame, path: Path = CPI_RELEASE_PATH) -> pd.DataFrame:
    cpi = cpi.copy()
    next_month = cpi["period"] + pd.DateOffset(months=1)
    cpi["release_date"] = next_month + pd.Timedelta(days=FALLBACK_RELEASE_DAY - 1)
    cpi["release_source"] = "estimasi_konservatif"

    if path.exists():
        official = pd.read_csv(path, parse_dates=["period", "release_date"])
        official = official.dropna(subset=["release_date"])[["period", "release_date"]]
        if len(official):
            merged = cpi.merge(official, on="period", how="left", suffixes=("", "_official"))
            has_official = merged["release_date_official"].notna()
            merged.loc[has_official, "release_date"] = merged.loc[has_official, "release_date_official"]
            merged.loc[has_official, "release_source"] = "bls_resmi"
            cpi = merged.drop(columns=["release_date_official"])

    return cpi


def build_cpi_table() -> pd.DataFrame:
    cpi = load_cpi_raw()
    # YoY dihitung dari seluruh seri dulu, supaya tahun 2021 punya pembanding 2020
    cpi["cpi_yoy_pct"] = (cpi["cpi"] / cpi["cpi"].shift(12) - 1) * 100
    cpi = build_release_dates(cpi)
    cpi = cpi[cpi["period"] >= "2021-01-01"].reset_index(drop=True)
    cpi.to_csv(CPI_OUT_PATH, index=False)
    return cpi


def align_cpi_to_prices(prices: pd.DataFrame, cpi: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Untuk setiap tanggal harga, ambil CPI terakhir yang SUDAH dirilis
    pada tanggal itu atau sebelumnya. Tidak ada data masa depan yang ikut.
    """
    if cpi is None:
        cpi = pd.read_csv(CPI_OUT_PATH, parse_dates=["period", "release_date"])

    left = prices[["date", "close"]].copy()
    left["date"] = pd.to_datetime(left["date"]).astype("datetime64[ns]")
    left = left.sort_values("date")

    right = cpi.dropna(subset=["release_date"])[["release_date", "cpi", "cpi_yoy_pct"]].copy()
    right["release_date"] = pd.to_datetime(right["release_date"]).astype("datetime64[ns]")
    right = right.sort_values("release_date")

    return pd.merge_asof(
        left,
        right,
        left_on="date",
        right_on="release_date",
        direction="backward",
    )

def add_macro_features(feat: pd.DataFrame) -> pd.DataFrame:
    aligned = align_cpi_to_prices(feat[["date", "close"]])
    return feat.merge(aligned[["date", "cpi_yoy_pct"]], on="date", how="left")
if __name__ == "__main__":
    cpi = build_cpi_table()
    print(cpi.tail(3).to_string())
    print("\nSumber tanggal rilis:", cpi["release_source"].value_counts().to_dict())
    print(f"Disimpan di: {CPI_OUT_PATH}")