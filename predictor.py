import logging
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _compute_rsi(series, period=14):
    if len(series) < period + 1:
        return 50
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.tail(period).mean()
    avg_loss = losses.tail(period).mean()
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _compute_sma(series, period=20):
    if len(series) < period:
        return series.mean()
    return series.tail(period).mean()


def fetch_stock(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="2mo")
        if hist is None or hist.empty:
            return None
        latest = hist.iloc[-1]
        prev_close = hist.iloc[-2] if len(hist) > 1 else latest
        close_series = hist["Close"]
        volume_series = hist["Volume"]
        avg_vol_20 = volume_series.tail(20).mean()

        change = round(float(latest["Close"] - prev_close["Close"]), 2)
        change_pct = round(float(change / prev_close["Close"] * 100), 2)
        sma_20 = round(float(_compute_sma(close_series, 20)), 2)
        rsi_14 = _compute_rsi(close_series, 14)
        volume_ratio = round(float(latest["Volume"] / avg_vol_20), 2) if avg_vol_20 > 0 else 1.0
        above_sma = bool(latest["Close"] >= sma_20)

        if len(close_series) >= 5:
            five_days_ago = close_series.iloc[-5]
            mom_5d = round(float((latest["Close"] - five_days_ago) / five_days_ago * 100), 2)
        else:
            mom_5d = change_pct

        info = yf.Ticker(ticker).info if hasattr(yf.Ticker(ticker), "info") else {}
        name = info.get("longName", info.get("shortName", ticker))

        return {
            "ticker": ticker.upper(),
            "name": name,
            "price": round(float(latest["Close"]), 2),
            "change": change,
            "change_pct": change_pct,
            "volume": int(latest["Volume"]),
            "sma_20": sma_20,
            "above_sma": above_sma,
            "rsi_14": rsi_14,
            "volume_ratio": volume_ratio,
            "momentum_5d": mom_5d,
            "high_52w": round(float(latest["High"]), 2),
            "low_52w": round(float(latest["Low"]), 2),
        }
    except Exception as e:
        logging.warning(f"Failed to fetch {ticker}: {e}")
        return None


def generate_signal(data):
    score = 0
    reasons = []

    if data["rsi_14"] < 35:
        score += 2
        reasons.append("oversold RSI")
    elif data["rsi_14"] < 45:
        score += 1
        reasons.append("low RSI")

    if data["above_sma"] and data["change_pct"] > 0:
        score += 2
        reasons.append("above 20d MA with momentum")
    elif data["above_sma"]:
        score += 1
        reasons.append("above 20d MA")

    if data["volume_ratio"] > 1.5 and data["change_pct"] > 0:
        score += 1
        reasons.append("high volume confirmation")

    if data["momentum_5d"] > 5:
        score += 1
        reasons.append(f"strong 5d momentum ({data['momentum_5d']:+.1f}%)")
    elif data["momentum_5d"] < -5:
        score -= 1
        reasons.append(f"weak 5d momentum ({data['momentum_5d']:+.1f}%)")

    if data["rsi_14"] > 70:
        score -= 1
        reasons.append("overbought RSI")
    if not data["above_sma"] and data["change_pct"] < 0:
        score -= 1
        reasons.append("below 20d MA")

    if score >= 3:
        signal = "BUY"
    elif score >= 1:
        signal = "HOLD"
    else:
        signal = "WATCH"

    return signal, score, ", ".join(reasons) if reasons else "neutral signals"


def predict_targets(data):
    price = data["price"]
    change_pct = data["change_pct"]
    rsi = data["rsi_14"]
    mom_5d = data["momentum_5d"]
    above_sma = data["above_sma"]

    rsi_bias = 0
    if rsi < 30:
        rsi_bias = 0.5
    elif rsi < 40:
        rsi_bias = 0.25
    elif rsi > 70:
        rsi_bias = -0.5
    elif rsi > 60:
        rsi_bias = -0.25

    trend_bias = 0.3 if above_sma else -0.3

    eod_pct = change_pct * 0.3 + rsi_bias + trend_bias * 0.5
    eod = round(price * (1 + eod_pct / 100), 2)

    week_pct = mom_5d * 0.6 + rsi_bias * 1.5 + trend_bias
    week_pct = max(min(week_pct, 15), -15)
    week = round(price * (1 + week_pct / 100), 2)

    month_pct = mom_5d * 1.5 + rsi_bias * 3 + trend_bias * 2
    month_pct = max(min(month_pct, 25), -25)
    month = round(price * (1 + month_pct / 100), 2)

    annual_trend = 10 if above_sma else -5
    if rsi < 35:
        annual_trend = 15
    elif rsi > 70:
        annual_trend = -10
    year_pct = max(min(annual_trend + mom_5d * 0.5, 40), -30)
    year = round(price * (1 + year_pct / 100), 2)

    return {
        "eod": {"price": eod, "change_pct": round(eod_pct, 2)},
        "week": {"price": week, "change_pct": round(week_pct, 2)},
        "month": {"price": month, "change_pct": round(month_pct, 2)},
        "year": {"price": year, "change_pct": round(year_pct, 2)},
    }


def generate_insight(data, signal, targets):
    price = data["price"]
    rsi = data["rsi_14"]
    mom = data["momentum_5d"]

    signal_map = {"BUY": "bullish", "HOLD": "neutral", "WATCH": "bearish"}
    outlook = signal_map[signal]

    rsi_desc = "oversold" if rsi < 35 else "overbought" if rsi > 70 else "neutral"

    paragraphs = []
    paragraphs.append(
        f"{data['name']} ({data['ticker']}) is trading at ${price:.2f} with a {outlook} outlook. "
        f"RSI at {rsi:.0f} ({rsi_desc}) and 5-day momentum at {mom:+.1f}%."
    )

    if signal == "BUY":
        paragraphs.append(
            f"We expect upside momentum to carry the stock toward ${targets['week']['price']:.2f} within the week "
            f"and ${targets['month']['price']:.2f} over the next month, driven by favorable technical positioning."
        )
    elif signal == "WATCH":
        paragraphs.append(
            f"Caution warranted in the near term. A move below key support levels could see the stock "
            f"testing ${targets['week']['price']:.2f} within the week."
        )
    else:
        paragraphs.append(
            f"The stock is range-bound for now. A break above ${data['sma_20']:.2f} (20d MA) would turn us more bullish; "
            f"failure to hold current levels risks a pullback to ${targets['week']['price']:.2f}."
        )

    return "\n\n".join(paragraphs)
