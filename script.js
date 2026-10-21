/* ===== Konfigurasi ===== */
const API_BASE = "http://127.0.0.1:8000/api";
// Di GitHub Pages (bukan localhost), data dibaca dari snapshot JSON di folder static-api.
const STATIC_MODE = !["127.0.0.1", "localhost"].includes(window.location.hostname);
const STATIC_BASE = "static-api/";

const charts = {};
const demoUsed = new Set();
let newsCache = [];

const $ = (id) => document.getElementById(id);

const fmtUSD = (n) =>
  n == null
    ? "—"
    : "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct = (n) => (n == null ? "—" : (n >= 0 ? "+" : "") + Number(n).toFixed(2) + "%");
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ===== Akses data ===== */
function staticFileFor(path) {
  // "/price-history?days=180" menjadi "static-api/price-history.json"
  const name = path.split("?")[0].replace(/^\//, "");
  return STATIC_BASE + name + ".json";
}

async function fetchJson(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("HTTP " + res.status + " (" + url + ")");
  return res.json();
}

async function getData(path, mockKey) {
  // 1. Sumber utama: backend lokal, atau snapshot statis saat di GitHub Pages
  try {
    const url = STATIC_MODE ? staticFileFor(path) : API_BASE + path;
    return await fetchJson(url);
  } catch (err) {
    console.warn("Sumber utama gagal:", path, err);
  }

  // 2. Cadangan: snapshot statis saat backend lokal tidak aktif
  if (!STATIC_MODE) {
    try {
      const data = await fetchJson(staticFileFor(path));
      data.from_snapshot = true;
      return data;
    } catch (err) {
      console.warn("Snapshot juga gagal:", path, err);
    }
  }

  // 3. Terakhir: data DEMO
  if (mockKey && window.MOCK_DATA) {
    demoUsed.add(mockKey);
    return window.MOCK_DATA[mockKey];
  }
  return { data_status: "error", message: "Data tidak dapat dimuat." };
}

/* ===== Grafik dan status ===== */
function drawChart(id, config) {
  if (charts[id]) charts[id].destroy();
  const el = $(id);
  if (!el) return;
  charts[id] = new Chart(el, config);
}

const baseOptions = (extra = {}) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { labels: { color: "#8b92a3" } } },
  scales: {
    x: { ticks: { color: "#8b92a3", maxTicksLimit: 8 }, grid: { color: "#2a2f3b" } },
    y: { ticks: { color: "#8b92a3" }, grid: { color: "#2a2f3b" } },
  },
  ...extra,
});

function setStatusBadge(status) {
  const badge = $("data-status-badge");
  if (!badge) return;
  const map = {
    ready: ["badge-ok", "Data siap"],
    partial: ["badge-warn", "Sebagian siap"],
    not_ready: ["badge-warn", "Belum siap"],
    demo: ["badge-demo", "DEMO"],
    error: ["badge-warn", "Error"],
  };
  const [cls, text] = map[status] || ["badge-muted", status];
  badge.className = "badge " + cls;
  badge.textContent = text;
}

/* ===== Navigasi ===== */
function setupNav() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.target;
      document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b === btn));
      document.querySelectorAll(".page").forEach((p) =>
        p.classList.toggle("active", p.dataset.page === target)
      );
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

/* ===== Dashboard ===== */
function renderDashboard(d) {
  const price = d.price;
  const pred = d.prediction;
  const sent = d.sentiment;
  const macro = d.macro;
  const rec = d.recommendation || {};

  $("kpi-current-price").textContent = fmtUSD(price?.close);
  $("kpi-current-date").textContent = price ? "Per " + price.date : "Data belum tersedia";
  $("kpi-change-1d").textContent = fmtPct(price?.change_1d_percent);
  $("kpi-predicted-price").textContent = fmtUSD(pred?.predicted_price);
  $("kpi-predicted-change").textContent = fmtPct(pred?.predicted_change_percent);
  $("kpi-target-date").textContent = pred ? "Target: " + pred.target_date : "";
  $("kpi-sentiment-summary").textContent = sent
    ? `${sent.percent.positive}% / ${sent.percent.neutral}% / ${sent.percent.negative}%`
    : "Belum tersedia";

  $("kpi-cpi").textContent = macro ? macro.cpi_yoy_percent.toFixed(2) + "%" : "—";
  $("kpi-cpi-sub").textContent = macro
    ? `Periode ${macro.period} · rilis ${macro.release_date} (${macro.release_source === "bls_resmi" ? "resmi" : "estimasi"})`
    : "Belum tersedia";

  const sig = $("recommendation-signal");
  sig.textContent = rec.signal ?? "—";
  sig.dataset.signal = rec.signal ?? "none";
  $("recommendation-reasons").innerHTML = (rec.reasons || []).map((r) => `<li>${esc(r)}</li>`).join("");

  const msgs = [...(d.messages || [])];
  if (d.from_snapshot) msgs.push("Menampilkan snapshot data (backend lokal tidak aktif).");
  $("dashboard-messages").textContent = msgs.join(" | ");
}

function renderHistory(h) {
  drawChart("chart-dashboard-history", {
    type: "line",
    data: {
      labels: h.dates || [],
      datasets: [{
        label: "Harga Close",
        data: h.closes || [],
        borderColor: "#f5c542",
        backgroundColor: "rgba(245,197,66,0.08)",
        fill: true,
        pointRadius: 0,
        tension: 0.2,
      }],
    },
    options: baseOptions(),
  });
}

/* ===== Price Forecast ===== */
function renderForecast(f) {
  const p = f.prediction;
  const m = f.metrics || {};
  $("forecast-price").textContent = fmtUSD(p?.predicted_price);
  $("forecast-target").textContent = p ? "Target: " + p.target_date : "Belum tersedia";
  $("forecast-change").textContent = fmtPct(p?.predicted_change_percent);
  $("forecast-acuan").textContent = p ? "Acuan: " + p.as_of_date : "";
  $("metric-direction").textContent =
    m.directional_accuracy != null ? (m.directional_accuracy * 100).toFixed(1) + "%" : "—";

  $("metric-mae-model").textContent = m.model ? m.model.MAE : "—";
  $("metric-rmse-model").textContent = m.model ? m.model.RMSE : "—";
  $("metric-mae-baseline").textContent = m.baseline_last_price ? m.baseline_last_price.MAE : "—";
  $("metric-rmse-baseline").textContent = m.baseline_last_price ? m.baseline_last_price.RMSE : "—";
  $("forecast-message").textContent = f.message || "";

  const s = f.test_series;
  if (!s) return;
  drawChart("chart-forecast", {
    type: "line",
    data: {
      labels: s.dates,
      datasets: [
        { label: "Aktual", data: s.actual, borderColor: "#f5c542", pointRadius: 0, tension: 0.2 },
        { label: "Prediksi XGBoost", data: s.predicted, borderColor: "#3b82f6", pointRadius: 0, tension: 0.2 },
        { label: "Baseline", data: s.baseline, borderColor: "#8b92a3", borderDash: [5, 5], pointRadius: 0 },
      ],
    },
    options: baseOptions(),
  });
}

/* ===== Sentiment ===== */
function renderSentiment(s) {
  const pct = s.summary?.percent;
  $("sentiment-positive-pct").textContent = pct ? pct.positive + "%" : "—";
  $("sentiment-neutral-pct").textContent = pct ? pct.neutral + "%" : "—";
  $("sentiment-negative-pct").textContent = pct ? pct.negative + "%" : "—";
  $("sentiment-message").textContent = s.message || "";

  const counts = s.summary?.counts;
  if (counts) {
    drawChart("chart-sentiment-doughnut", {
      type: "doughnut",
      data: {
        labels: ["Positif", "Netral", "Negatif"],
        datasets: [{
          data: [counts.positive, counts.neutral, counts.negative],
          backgroundColor: ["#2ecc71", "#8b92a3", "#e74c3c"],
          borderWidth: 0,
        }],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: "#8b92a3" } } } },
    });
  }

  if (s.trend) {
    drawChart("chart-sentiment-trend", {
      type: "bar",
      data: {
        labels: s.trend.map((t) => t.date),
        datasets: [
          { label: "Positif", data: s.trend.map((t) => t.positive), backgroundColor: "#2ecc71" },
          { label: "Netral", data: s.trend.map((t) => t.neutral), backgroundColor: "#8b92a3" },
          { label: "Negatif", data: s.trend.map((t) => t.negative), backgroundColor: "#e74c3c" },
        ],
      },
      options: baseOptions({
        scales: {
          x: { stacked: true, ticks: { color: "#8b92a3", maxTicksLimit: 8 }, grid: { color: "#2a2f3b" } },
          y: { stacked: true, ticks: { color: "#8b92a3" }, grid: { color: "#2a2f3b" } },
        },
      }),
    });
  }
}

/* ===== Economic News ===== */
function renderNewsCategories(categories) {
  const sel = $("news-category");
  const current = sel.value;
  sel.innerHTML =
    '<option value="">Semua kategori</option>' +
    (categories || []).map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  sel.value = current;
}

function renderNewsTable(items) {
  const tbody = $("news-table-body");
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="muted">Tidak ada berita yang cocok.</td></tr>`;
  } else {
    tbody.innerHTML = items.map((n) => {
      const sent = (n.sentiment || "").toLowerCase();
      const score = n.confidence !== "" && n.confidence != null ? (Number(n.confidence) * 100).toFixed(1) + "%" : "—";
      const link = n.url && n.url !== "#"
        ? `<a href="${esc(n.url)}" target="_blank" rel="noopener">Buka</a>`
        : "—";
      return `
        <tr>
          <td>${esc(n.date)}</td>
          <td>${esc(n.title)}</td>
          <td>${esc(n.source)}</td>
          <td>${esc(n.category)}</td>
          <td><span class="tag tag-${esc(sent)}">${esc(sent)}</span></td>
          <td>${score}</td>
          <td>${link}</td>
        </tr>`;
    }).join("");
  }
  $("news-count").textContent = `Menampilkan ${items.length} berita`;
}

function filterNewsLocally(items) {
  const q = $("news-search").value.trim().toLowerCase();
  const cat = $("news-category").value;
  const sent = $("news-sentiment").value;
  return items.filter((n) =>
    (!q || (n.title || "").toLowerCase().includes(q) || (n.source || "").toLowerCase().includes(q)) &&
    (!cat || n.category === cat) &&
    (!sent || (n.sentiment || "").toLowerCase() === sent)
  );
}

async function loadNews() {
  const params = new URLSearchParams({
    q: $("news-search").value.trim(),
    category: $("news-category").value,
    sentiment: $("news-sentiment").value,
  });
  const data = await getData(`/news?${params.toString()}`, "news");

  if (data.data_status !== "ready" && data.data_status !== "demo") {
    renderNewsTable([]);
    $("news-count").textContent = data.message || "Data berita belum siap.";
    return;
  }

  // Filter selalu dijalankan di browser, sehingga snapshot statis tetap bisa difilter
  newsCache = data.items || [];
  renderNewsCategories(data.categories);
  renderNewsTable(filterNewsLocally(newsCache));
}

function bindNewsFilters() {
  let timer;
  $("news-search").addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(loadNews, 300);
  });
  $("news-category").addEventListener("change", loadNews);
  $("news-sentiment").addEventListener("change", loadNews);
}

/* ===== Jam dashboard (WIB) ===== */
function startClock() {
  const timeEl = $("live-time");
  const dateEl = $("live-date");
  if (!timeEl || !dateEl) return;

  const timeFmt = new Intl.DateTimeFormat("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "Asia/Jakarta",
  });
  const dateFmt = new Intl.DateTimeFormat("id-ID", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Jakarta",
  });

  const tick = () => {
    const now = new Date();
    timeEl.textContent = timeFmt.format(now).replace(/\./g, ":") + " WIB";
    dateEl.textContent = dateFmt.format(now);
  };
  tick();
  setInterval(tick, 1000);
}

/* ===== Inisialisasi ===== */
async function init() {
  setupNav();
  bindNewsFilters();
  startClock();

  const [dash, history, forecast, sentiment] = await Promise.all([
    getData("/dashboard", "dashboard"),
    getData("/price-history?days=180", "history"),
    getData("/forecast", "forecast"),
    getData("/sentiment", "sentiment"),
  ]);

  renderDashboard(dash);
  renderHistory(history);
  renderForecast(forecast);
  renderSentiment(sentiment);
  await loadNews();

  const statuses = [dash, history, forecast, sentiment].map((x) => x.data_status);
  setStatusBadge(demoUsed.size ? "demo" : statuses.every((s) => s === "ready") ? "ready" : "not_ready");
  $("demo-banner").classList.toggle("hidden", demoUsed.size === 0);
}

document.addEventListener("DOMContentLoaded", init);