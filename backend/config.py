from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ARTIFACT_DIR = BASE_DIR / "artifacts"

PRICE_DATA_PATH = DATA_DIR / "harga_emas.xlsx"
NEWS_DATA_PATH = DATA_DIR / "berita_ekonomi.csv"

MODEL_PATH = ARTIFACT_DIR / "xgboost_gold.json"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"
FORECAST_TEST_PATH = ARTIFACT_DIR / "forecast_test.csv"
SENTIMENT_PATH = ARTIFACT_DIR / "news_sentiment.csv"

HORIZON_DAYS = 21          # ± satu bulan bursa
TRAIN_RATIO = 0.8          # pembagian data berbasis waktu
FINBERT_MODEL = "ProsusAI/finbert"