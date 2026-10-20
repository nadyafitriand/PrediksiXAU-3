import pandas as pd

from config import ARTIFACT_DIR, FINBERT_MODEL, NEWS_DATA_PATH, SENTIMENT_PATH
from processing.clean_news_data import load_news_data

BATCH_SIZE = 16
MAX_LENGTH = 512

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline  # import di sini agar error jelas jika belum terpasang

        _pipeline = pipeline(
            "text-classification",
            model=FINBERT_MODEL,
            tokenizer=FINBERT_MODEL,
            top_k=None,
        )
    return _pipeline


def classify_texts(texts: list[str]) -> list[dict]:
    pipe = _get_pipeline()
    raw = pipe(texts, batch_size=BATCH_SIZE, truncation=True, max_length=MAX_LENGTH)

    results = []
    for scores in raw:
        probs = {item["label"].lower(): float(item["score"]) for item in scores}
        label = max(probs, key=probs.get)
        results.append({
            "sentiment": label,
            "confidence": round(probs[label], 4),
            "prob_positive": round(probs.get("positive", 0.0), 4),
            "prob_neutral": round(probs.get("neutral", 0.0), 4),
            "prob_negative": round(probs.get("negative", 0.0), 4),
        })
    return results


def run_sentiment_analysis() -> pd.DataFrame:
    news = load_news_data(NEWS_DATA_PATH)
    if news.empty:
        raise ValueError("Tidak ada berita valid untuk dianalisis.")

    results = classify_texts(news["text"].tolist())
    out = pd.concat(
        [
            news[["date", "title", "source", "url", "category"]].reset_index(drop=True),
            pd.DataFrame(results),
        ],
        axis=1,
    )
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(SENTIMENT_PATH, index=False)
    return out


def load_sentiment_results() -> pd.DataFrame:
    if not SENTIMENT_PATH.exists():
        raise FileNotFoundError(
            "Hasil FinBERT belum tersedia. Jalankan: python -m models.analyze_sentiment"
        )
    return pd.read_csv(SENTIMENT_PATH, parse_dates=["date"])


if __name__ == "__main__":
    df = run_sentiment_analysis()
    print(df["sentiment"].value_counts())
    print(f"\nHasil disimpan di: {SENTIMENT_PATH}")