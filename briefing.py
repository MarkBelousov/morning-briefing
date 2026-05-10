import json
import os
from datetime import datetime, timezone, timedelta
from fetcher import fetch_market_data, fetch_stock_data, generate_recommendations
from headlines import fetch_headlines
from insights import generate_insights

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def generate_briefing():
    market_data = fetch_market_data()
    stock_data = fetch_stock_data()
    recommendations = generate_recommendations(stock_data)
    headlines = fetch_headlines()
    insights = generate_insights(market_data, recommendations)

    now = datetime.now(timezone(timedelta(hours=-4)))
    briefing = {
        "date": now.strftime("%A, %B %d, %Y"),
        "timestamp": now.isoformat(),
        "market_data": market_data,
        "stock_picks": recommendations,
        "headlines": headlines,
        "insights": insights,
        "summary": _generate_summary(market_data),
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    filename = f"briefing_{now.strftime('%Y-%m-%d')}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(briefing, f, indent=2, default=str)

    latest_path = os.path.join(DATA_DIR, "latest.json")
    with open(latest_path, "w") as f:
        json.dump(briefing, f, indent=2, default=str)

    return briefing


def _generate_summary(market_data):
    lines = []
    for category in ("US Indices", "Commodities", "Forex"):
        items = market_data.get(category, {})
        for name, data in items.items():
            if not data or "change_pct" not in data:
                continue
            arrow = "▲" if data.get("change_pct", 0) >= 0 else "▼"
            lines.append(f"{name}: {data.get('price', 'N/A')}  {arrow} {data.get('change_pct', 0):+.2f}%")
    return "\n".join(lines[:12])


def load_latest_briefing():
    latest_path = os.path.join(DATA_DIR, "latest.json")
    if os.path.exists(latest_path):
        with open(latest_path) as f:
            return json.load(f)
    return None


def list_briefings():
    if not os.path.exists(DATA_DIR):
        return []
    files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.startswith("briefing_") and f.endswith(".json")],
        reverse=True,
    )
    return files


def load_briefing(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


if __name__ == "__main__":
    briefing = generate_briefing()
    print(f"Briefing generated for {briefing['date']}")
    print()
    for section in briefing.get("insights", []):
        print(f"## {section['title']}")
        print(section["body"])
        print()
    if briefing.get("stock_picks", {}).get("buys"):
        print("--- BUY PICKS ---")
        for p in briefing["stock_picks"]["buys"][:5]:
            print(f"  {p['ticker']}: ${p['price']} ({p['change_pct']:+.1f}%) | RSI {p['rsi']} | {p['reasons']}")
