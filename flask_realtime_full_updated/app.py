
from flask import Flask, render_template, request, Response, stream_with_context, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
import time, json
from datetime import datetime
import skfuzzy as fuzz

app = Flask(__name__)
# In-memory store for price history per symbol
HISTORY = {}

def fetch_latest_price(symbol, interval):
    try:
        df = yf.Ticker(symbol).history(period="1d", interval=interval)
        if df is None or df.empty:
            return None, None
        df = df.reset_index()
        # Try different datetime column names for compatibility
        dt_col = 'Datetime' if 'Datetime' in df.columns else ('Date' if 'Date' in df.columns else df.columns[0])
        ts = pd.to_datetime(df[dt_col].iloc[-1])
        price = float(df['Close'].iloc[-1])
        return ts.isoformat(), price
    except Exception:
        return None, None

def compute_fuzzy_envelope_live(values, n_clusters=3, m=2.0):
    arr = np.asarray(values, dtype=float)
    N = arr.size
    if N == 0:
        return [], [], []
    if N == 1:
        return arr.tolist(), arr.tolist(), np.ones((1,1)).tolist()
    x_min, x_max = arr.min(), arr.max()
    if x_max == x_min:
        lower = np.full(N, x_min)
        upper = np.full(N, x_min)
        memberships = np.ones((1, N))
        return lower.tolist(), upper.tolist(), memberships.tolist()
    norm = (arr - x_min) / (x_max - x_min)
    data = norm[np.newaxis, :]
    try:
        cntr, u, *_ = fuzz.cluster.cmeans(data, c=min(n_clusters, N), m=m, error=1e-6, maxiter=200)
    except Exception:
        mean = pd.Series(arr).rolling(window=max(1, N//10), min_periods=1).mean().to_numpy()
        std = pd.Series(arr).rolling(window=max(1, N//10), min_periods=1).std().fillna(0).to_numpy()
        return (mean-std).tolist(), (mean+std).tolist(), np.ones((1, N)).tolist()
    centroids = cntr.flatten() * (x_max - x_min) + x_min
    memberships = u
    denom = memberships.sum(axis=0) + 1e-9
    weighted_mean = (memberships.T @ centroids) / denom
    dif = (centroids[:, np.newaxis] - weighted_mean[np.newaxis, :]) ** 2
    weighted_var = (memberships * dif).sum(axis=0) / denom
    weighted_std = np.sqrt(np.maximum(weighted_var, 0.0))
    lower = weighted_mean - weighted_std
    upper = weighted_mean + weighted_std
    return lower.tolist(), upper.tolist(), memberships.tolist()

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stream")
def stream():
    """Server-Sent Events endpoint.
    Query params:
      symbol, interval, refresh (seconds), window (points), n_clusters, m, simulate
    """
    symbol = request.args.get("symbol", "AAPL").upper()
    interval = request.args.get("interval", "1m")
    refresh = max(1, int(request.args.get("refresh", "5")))
    window = max(10, int(request.args.get("window", "120")))
    n_clusters = int(request.args.get("n_clusters", "3"))
    m = float(request.args.get("m", "2.0"))
    simulate = request.args.get("simulate", "true").lower() in ("1","true","yes")

    # ensure history structure exists
    if symbol not in HISTORY:
        HISTORY[symbol] = {"times": [], "prices": []}

    def event_stream():
        while True:
            ts, price = fetch_latest_price(symbol, interval)
            if ts is None or price is None:
                if simulate:
                    last = HISTORY[symbol]["prices"][-1] if HISTORY[symbol]["prices"] else 100.0
                    price = float(last * (1 + np.random.normal(0, 0.001)))
                    ts = datetime.utcnow().isoformat()
                else:
                    payload = {"ok": False, "reason": "no-data"}
                    yield f"data: {json.dumps(payload)}\n\n"
                    time.sleep(refresh)
                    continue

            # append/update history
            times = HISTORY[symbol]["times"]
            prices = HISTORY[symbol]["prices"]
            if times and pd.to_datetime(ts) <= pd.to_datetime(times[-1]):
                prices[-1] = price
                times[-1] = ts
            else:
                times.append(ts)
                prices.append(price)
                if len(prices) > window:
                    HISTORY[symbol]["times"] = times[-window:]
                    HISTORY[symbol]["prices"] = prices[-window:]
                else:
                    HISTORY[symbol]["times"] = times
                    HISTORY[symbol]["prices"] = prices

            lower, upper, memberships = compute_fuzzy_envelope_live(np.array(HISTORY[symbol]["prices"]), n_clusters=n_clusters, m=m)
            payload = {
                "ok": True,
                "symbol": symbol,
                "times": HISTORY[symbol]["times"],
                "prices": HISTORY[symbol]["prices"],
                "lower": lower,
                "upper": upper,
                "memberships": memberships,
                "last": {"time": ts, "price": price},
                "updated": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(payload, default=str)}\n\n"
            time.sleep(refresh)
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})


import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
