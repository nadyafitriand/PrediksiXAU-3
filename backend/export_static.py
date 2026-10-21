import json
from pathlib import Path

from services import dashboard_service as svc

OUT = Path(__file__).resolve().parent.parent / "static-api"
OUT.mkdir(exist_ok=True)


def _default(o):
    if hasattr(o, "item"):
        return o.item()
    return str(o)


files = {
    "dashboard.json": svc.get_dashboard(),
    "price-history.json": svc.get_price_history(180),
    "forecast.json": svc.get_forecast(),
    "sentiment.json": svc.get_sentiment(),
    "news.json": svc.get_news(),
}

for name, data in files.items():
    data["static"] = True
    (OUT / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=_default),
        encoding="utf-8",
    )
    print("tulis", name)

print("Selesai, file ada di", OUT)