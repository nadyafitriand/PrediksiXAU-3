from pathlib import Path

import pandas as pd

from config import PRICE_DATA_PATH

COLUMN_ALIASES = {
    "date": ["date", "tanggal", "time", "datetime"],
    "open": ["open", "pembukaan"],
    "high": ["high", "tertinggi"],
    "low": ["low", "terendah"],
    "close": ["close", "price", "terakhir", "penutupan", "close price"],
    "volume": ["volume", "vol"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename, used = {}, set()
    for original in df.columns:
        low = str(original).strip().lower()
        for std, aliases in COLUMN_ALIASES.items():
            if std not in used and low in aliases:
                rename[original] = std
                used.add(std)
                break
    return df.rename(columns=rename)


def _read_raw(path: Path) -> pd.DataFrame:
    with open(path, "rb") as f:
        head = f.read(512)

    if head.startswith(b"PK"):                       # .xlsx asli (zip)
        return pd.read_excel(path, engine="openpyxl")
    if head.startswith(b"\xd0\xcf\x11\xe0"):         # .xls lama (perlu: pip install xlrd==2.0.1)
        return pd.read_excel(path, engine="xlrd")

    text = head.decode("utf-8", errors="ignore").lower()
    if "<html" in text or "<table" in text:          # HTML hasil unduhan
        tables = pd.read_html(path)
        if not tables:
            raise ValueError("File HTML tidak berisi tabel.")
        return max(tables, key=len)

    # CSV: pemisah koma atau titik koma dideteksi otomatis
    try:
        return pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=None, engine="python", encoding="latin1")


def load_price_data(path: Path = PRICE_DATA_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset harga tidak ditemukan: {path}")

    df = _read_raw(path)
    df = _normalize_columns(df)
    if "date" not in df or "close" not in df:
        raise ValueError(
            f"Kolom wajib 'date' dan 'close' tidak ditemukan. Kolom tersedia: {list(df.columns)}"
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    df = df.dropna(subset=["date", "close"])
    df = df[df["close"] > 0]
    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    if len(df) == 0:
        raise ValueError("Tidak ada baris harga yang valid setelah pembersihan.")
    return df