from pathlib import Path

import pandas as pd

from config import NEWS_DATA_PATH

NEWS_ALIASES = {
    "date": ["date", "tanggal", "published", "published_at", "pubdate", "time"],
    "title": ["title", "judul", "headline"],
    "description": ["description", "deskripsi", "content", "text", "isi", "summary"],
    "source": ["source", "sumber", "publisher"],
    "url": ["url", "link"],
    "category": ["category", "kategori", "indicator", "indikator"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename, used = {}, set()
    for original in df.columns:
        low = str(original).strip().lower()
        for std, aliases in NEWS_ALIASES.items():
            if std not in used and low in aliases:
                rename[original] = std
                used.add(std)
                break
    return df.rename(columns=rename)


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin1")


def load_news_data(path: Path = NEWS_DATA_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset berita tidak ditemukan: {path}")

    df = _normalize_columns(_read_csv(path))
    if "date" not in df or "title" not in df:
        raise ValueError(
            f"Kolom wajib 'date' dan 'title' tidak ditemukan. Kolom tersedia: {list(df.columns)}"
        )

    for col in ["description", "source", "url", "category"]:
        if col not in df:
            df[col] = ""

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["title"] = df["title"].fillna("").astype(str).str.strip()
    df["description"] = df["description"].fillna("").astype(str).str.strip()
    df["source"] = df["source"].fillna("").astype(str)
    df["url"] = df["url"].fillna("").astype(str)
    df["category"] = df["category"].fillna("").astype(str)

    df = df.dropna(subset=["date"])
    df = df[df["title"] != ""]
    df["text"] = (df["title"] + ". " + df["description"]).str.strip()
    df = (
        df.drop_duplicates(subset=["title", "date"])
        .sort_values("date", ascending=False)
        .reset_index(drop=True)
    )
    return df