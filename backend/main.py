from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from services import dashboard_service as svc

app = FastAPI(title="GoldVision API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard():
    return svc.get_dashboard()


@app.get("/api/price-history")
def price_history(days: int = Query(180, ge=10, le=2000)):
    return svc.get_price_history(days)


@app.get("/api/forecast")
def forecast():
    return svc.get_forecast()


@app.get("/api/sentiment")
def sentiment():
    return svc.get_sentiment()


@app.get("/api/news")
def news(
    q: str = "",
    category: str = "",
    sentiment: str = "",
):
    return svc.get_news(q=q, category=category, sentiment=sentiment)