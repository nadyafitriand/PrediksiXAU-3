/* DATA SIMULASI, hanya dipakai saat backend tidak terhubung.
   Angka di file ini bukan hasil model dan selalu ditampilkan dengan label DEMO.
   Tanggal dibuat mundur dari 31 Desember 2025 agar sesuai rentang data asli. */
(function () {
  const END = new Date(2025, 11, 31);
  const days = [];
  const cur = new Date(END);
  while (days.length < 180) {
    if (cur.getDay() !== 0 && cur.getDay() !== 6) days.unshift(new Date(cur));
    cur.setDate(cur.getDate() - 1);
  }

  const fmt = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

  const dates = days.map(fmt);
  const closes = [];
  let price = 4050;
  days.forEach((_, i) => {
    price += Math.sin(i / 9) * 12 + ((i * 37) % 11 - 5);
    closes.push(Math.round(price * 100) / 100);
  });

  const last = closes[closes.length - 1];
  const prev = closes[closes.length - 2];
  const change1d = ((last - prev) / prev) * 100;
  const demoPredPct = 1.2;
  const predicted = Math.round(last * (1 + demoPredPct / 100) * 100) / 100;

  const sentimentCounts = { positive: 38, neutral: 45, negative: 57 };
  const total = sentimentCounts.positive + sentimentCounts.neutral + sentimentCounts.negative;
  const sentimentPercent = {
    positive: +((sentimentCounts.positive / total) * 100).toFixed(2),
    neutral: +((sentimentCounts.neutral / total) * 100).toFixed(2),
    negative: +((sentimentCounts.negative / total) * 100).toFixed(2),
  };

  const trend = dates.slice(-20).map((day, idx) => ({
    date: day,
    positive: 1 + (idx % 3),
    neutral: 2 + (idx % 4),
    negative: 1 + ((idx + 1) % 3),
  }));

  const newsItems = [1, 2, 3, 4, 5, 6].map((n, idx) => ({
    date: dates[dates.length - 1 - idx * 2],
    title: `[CONTOH DEMO] Judul berita ekonomi AS #${n}`,
    source: "Sumber Contoh",
    url: "#",
    category: ["Fed/FOMC", "CPI", "Jobs/NFP"][idx % 3],
    sentiment: ["positive", "neutral", "negative"][idx % 3],
    confidence: 0.85,
    prob_positive: 0.1,
    prob_neutral: 0.1,
    prob_negative: 0.8,
  }));

  window.MOCK_DATA = {
    dashboard: {
      data_status: "demo",
      messages: ["Data simulasi (DEMO)"],
      price: { date: dates[dates.length - 1], close: last, change_1d_percent: +change1d.toFixed(2), data_rows: 180 },
      prediction: {
        as_of_date: dates[dates.length - 1],
        target_date: "DEMO",
        horizon_trading_days: 21,
        current_price: last,
        predicted_price: predicted,
        predicted_change_percent: demoPredPct,
      },
      sentiment: { total, counts: sentimentCounts, percent: sentimentPercent },
      recommendation: {
        signal: "Buy",
        reasons: ["DEMO: indikasi ini hanya contoh tampilan, bukan hasil aturan pada data nyata."],
        rule_based: true,
        disclaimer: "Indikasi berbasis aturan penelitian, bukan jaminan keuntungan atau nasihat investasi.",
      },
    },
    history: { data_status: "demo", dates, closes },
    forecast: {
      data_status: "demo",
      message: "Data simulasi (DEMO)",
      horizon_days: 21,
      prediction: null,
      metrics: {
        model: { MAE: 0, RMSE: 0 },
        baseline_last_price: { MAE: 0, RMSE: 0 },
        directional_accuracy: 0,
      },
      test_series: {
        dates: dates.slice(-60),
        actual: closes.slice(-60),
        predicted: closes.slice(-60),
        baseline: closes.slice(-60),
      },
    },
    sentiment: {
      data_status: "demo",
      summary: { total, counts: sentimentCounts, percent: sentimentPercent },
      trend,
    },
    news: {
      data_status: "demo",
      categories: ["CPI", "Fed/FOMC", "Jobs/NFP"],
      items: newsItems,
    },
  };
})();