import yfinance as yf
import config
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _get_hist(ticker, period="2mo"):
    try:
        return yf.Ticker(ticker).history(period=period)
    except Exception:
        return None


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


def fetch_market_data():
    results = {}
    all_tickers = []
    for category, tickers in config.TICKERS.items():
        for name, ticker in tickers.items():
            all_tickers.append(ticker)
    all_tickers.append(config.VOLATILITY_INDEX)

    for i in range(0, len(all_tickers), 50):
        batch = all_tickers[i:i+50]
        try:
            yf.download(tickers=batch, period="5d", interval="1d", auto_adjust=True, progress=False, threads=True)
        except Exception:
            pass

    for ticker in all_tickers:
        try:
            hist = _get_hist(ticker, "2mo")
            if hist is None or hist.empty:
                continue
            latest = hist.iloc[-1]
            prev_close = hist.iloc[-2] if len(hist) > 1 else latest
            info = {
                "price": round(float(latest["Close"]), 2),
                "change": round(float(latest["Close"] - prev_close["Close"]), 2),
                "change_pct": round(float((latest["Close"] - prev_close["Close"]) / prev_close["Close"] * 100), 2),
                "high": round(float(latest["High"]), 2),
                "low": round(float(latest["Low"]), 2),
                "volume": int(latest["Volume"]) if "Volume" in latest and latest["Volume"] else 0,
            }
            if len(hist) >= 20:
                info["ytd_change_pct"] = round(float((latest["Close"] - hist.iloc[-20]["Close"]) / hist.iloc[-20]["Close"] * 100), 2)
                info["sma_20"] = round(float(_compute_sma(hist["Close"], 20)), 2)
                info["rsi_14"] = _compute_rsi(hist["Close"], 14)
                avg_vol = hist["Volume"].tail(20).mean()
                info["volume_ratio"] = round(float(info["volume"] / avg_vol), 2) if avg_vol > 0 else 1.0
            else:
                info["ytd_change_pct"] = 0.0
                info["sma_20"] = info["price"]
                info["rsi_14"] = 50.0
                info["volume_ratio"] = 1.0
            results[ticker] = info
        except Exception as e:
            logging.warning(f"Failed to parse {ticker}: {e}")
            continue

    structured = {}
    for category, tickers in config.TICKERS.items():
        structured[category] = {}
        for name, ticker in tickers.items():
            data = results.get(ticker, {})
            data["name"] = name
            structured[category][name] = data

    if config.VOLATILITY_INDEX in results:
        structured["Volatility"] = {"VIX": results[config.VOLATILITY_INDEX]}

    return structured


def fetch_stock_data():
    all_stocks = []
    for sector, stocks in config.TRACKED_STOCKS.items():
        for s in stocks:
            all_stocks.append(s)

    results = {}
    for ticker in all_stocks:
        try:
            hist = _get_hist(ticker, "2mo")
            if hist is None or hist.empty:
                continue
            latest = hist.iloc[-1]
            prev_close = hist.iloc[-2] if len(hist) > 1 else latest
            close_series = hist["Close"]
            volume_series = hist["Volume"]
            avg_vol_20 = volume_series.tail(20).mean()

            change_pct = round(float((latest["Close"] - prev_close["Close"]) / prev_close["Close"] * 100), 2)
            sma_20 = round(float(_compute_sma(close_series, 20)), 2)
            rsi_14 = _compute_rsi(close_series, 14)
            volume_ratio = round(float(latest["Volume"] / avg_vol_20), 2) if avg_vol_20 > 0 else 1.0
            above_sma = latest["Close"] >= sma_20

            if len(close_series) >= 5:
                five_days_ago = close_series.iloc[-5]
                mom_5d = round(float((latest["Close"] - five_days_ago) / five_days_ago * 100), 2)
            else:
                mom_5d = change_pct

            results[ticker] = {
                "price": round(float(latest["Close"]), 2),
                "change_pct": change_pct,
                "change": round(float(latest["Close"] - prev_close["Close"]), 2),
                "volume": int(latest["Volume"]),
                "sma_20": sma_20,
                "above_sma": above_sma,
                "rsi_14": rsi_14,
                "volume_ratio": volume_ratio,
                "momentum_5d": mom_5d,
            }
        except Exception as e:
            logging.warning(f"Failed to fetch stock {ticker}: {e}")
            continue

    return results


def generate_recommendations(stock_data):
    buys = []
    holds = []
    watches = []

    for ticker, data in stock_data.items():
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

        item = {
            "ticker": ticker,
            "price": data["price"],
            "change_pct": data["change_pct"],
            "signal": signal,
            "score": score,
            "rsi": data["rsi_14"],
            "above_sma": data["above_sma"],
            "volume_ratio": data["volume_ratio"],
            "momentum_5d": data["momentum_5d"],
            "reasons": ", ".join(reasons) if reasons else "neutral signals",
        }

        if signal == "BUY":
            buys.append(item)
        elif signal == "HOLD":
            holds.append(item)
        else:
            watches.append(item)

    buys.sort(key=lambda x: -x["score"])
    holds.sort(key=lambda x: -x["score"])
    watches.sort(key=lambda x: x["score"])

    return {"buys": buys[:8], "holds": holds[:5], "watches": watches[:5]}
