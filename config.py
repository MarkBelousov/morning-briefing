import os

TICKERS = {
    "US Indices": {
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "Dow Jones": "^DJI",
        "Russell 2000": "^RUT",
    },
    "Forex": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "USDJPY=X",
        "USD/CHF": "USDCHF=X",
        "USD/CAD": "USDCAD=X",
        "AUD/USD": "AUDUSD=X",
    },
    "Commodities": {
        "Gold": "GC=F",
        "Silver": "SI=F",
        "Crude Oil": "CL=F",
        "Natural Gas": "NG=F",
    },
    "Sectors": {
        "Tech (XLK)": "XLK",
        "Financials (XLF)": "XLF",
        "Energy (XLE)": "XLE",
        "Healthcare (XLV)": "XLV",
        "Industrials (XLI)": "XLI",
        "Consumer Disc (XLY)": "XLY",
    },
}

VOLATILITY_INDEX = "^VIX"

TRACKED_STOCKS = {
    "Tech Giants": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "ORCL"],
    "Semiconductors": ["TSM", "AMD", "INTC", "QCOM", "ASML"],
    "Financial": ["JPM", "GS", "BAC", "V", "MA", "BLK"],
    "Healthcare": ["UNH", "JNJ", "LLY", "PFE", "MRK", "ABBV"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Consumer": ["HD", "DIS", "NKE", "WMT", "COST", "SBUX"],
    "Industrial": ["CAT", "BA", "GE", "HON", "UPS"],
    "Defense": ["LMT", "RTX", "NOC", "GD"],
}

EMAIL = {
    "smtp_server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.environ.get("SMTP_PORT", 587)),
    "from": os.environ.get("EMAIL_FROM", "your.email@gmail.com"),
    "password": os.environ.get("EMAIL_PASSWORD", "your-app-password"),
}

CARRIER_GATEWAYS = {
    "verizon": "vtext.com",
    "att": "txt.att.net",
    "tmobile": "tmomail.net",
    "sprint": "messaging.sprintpcs.com",
    "google_fi": "msg.fi.google.com",
}

RSS_FEEDS = [
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories"),
]

TRIGGER_SECRET = os.environ.get("TRIGGER_SECRET", "change-this-to-a-random-string")
