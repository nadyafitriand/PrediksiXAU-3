RULES = {
    "buy_threshold_pct": 2.0,     # prediksi naik >= 2% -> kandidat Buy
    "sell_threshold_pct": -2.0,   # prediksi turun <= -2% -> kandidat Sell
    "sentiment_conflict_share_pct": 50.0,  # sentimen yang bertentangan dominan jika >= 50%
}


def build_recommendation(
    predicted_change_pct: float | None,
    sentiment_percent: dict | None = None,
    rules: dict = RULES,
) -> dict:
    """
    Aturan keputusan berbasis aturan (rule-based), bukan model machine learning.
    Prediksi harga adalah dasar utama; sentimen berfungsi sebagai penyaring
    yang bisa menahan sinyal Buy/Sell menjadi Hold.
    """
    base = {
        "rule_based": True,
        "rules": rules,
        "disclaimer": "Indikasi berbasis aturan penelitian, bukan jaminan keuntungan atau nasihat investasi.",
    }

    if predicted_change_pct is None:
        return {
            **base,
            "signal": None,
            "reasons": ["Prediksi harga belum tersedia, indikasi tidak dapat dibentuk."],
        }

    reasons = []
    if predicted_change_pct >= rules["buy_threshold_pct"]:
        signal = "Buy"
        reasons.append(
            f"Prediksi perubahan {predicted_change_pct:+.2f}% melampaui ambang Buy ({rules['buy_threshold_pct']}%)."
        )
    elif predicted_change_pct <= rules["sell_threshold_pct"]:
        signal = "Sell"
        reasons.append(
            f"Prediksi perubahan {predicted_change_pct:+.2f}% melampaui ambang Sell ({rules['sell_threshold_pct']}%)."
        )
    else:
        signal = "Hold"
        reasons.append(f"Prediksi perubahan {predicted_change_pct:+.2f}% berada dalam rentang Hold.")

    threshold = rules["sentiment_conflict_share_pct"]
    if sentiment_percent:
        pos = float(sentiment_percent.get("positive", 0))
        neu = float(sentiment_percent.get("neutral", 0))
        neg = float(sentiment_percent.get("negative", 0))

        if signal == "Buy" and neg >= threshold:
            signal = "Hold"
            reasons.append(
                f"Sentimen negatif dominan ({neg:.1f}%), sinyal Buy ditahan menjadi Hold."
            )
        elif signal == "Sell" and pos >= threshold:
            signal = "Hold"
            reasons.append(
                f"Sentimen positif dominan ({pos:.1f}%), sinyal Sell ditahan menjadi Hold."
            )
        else:
            reasons.append(
                f"Sentimen berita: positif {pos:.1f}%, netral {neu:.1f}%, negatif {neg:.1f}%; tidak mengubah sinyal."
            )
    else:
        reasons.append("Data sentimen belum tersedia; indikasi hanya berdasarkan prediksi harga.")

    return {**base, "signal": signal, "reasons": reasons}