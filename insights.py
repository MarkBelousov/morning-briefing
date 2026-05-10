import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def generate_insights(market_data, stock_recommendations=None):
    indices = market_data.get("US Indices", {})
    sectors = market_data.get("Sectors", {})
    commodities = market_data.get("Commodities", {})
    forex = market_data.get("Forex", {})
    vix_data = market_data.get("Volatility", {}).get("VIX", {})

    overview = _ai_overview(indices, sectors, commodities, forex, vix_data, stock_recommendations)
    picks = _stock_picks(stock_recommendations) if stock_recommendations else None
    sector = _sector_analysis(sectors)
    commodities_insight = _commodities_insight(commodities)
    forex_insight = _forex_insight(forex)
    macro = _macro_context(indices, vix_data)

    return [s for s in [overview, picks, sector, commodities_insight, forex_insight, macro] if s]


def _ai_overview(indices, sectors, commodities, forex, vix_data, recs=None):
    if not indices:
        return None

    up = [(n, d["change_pct"]) for n, d in indices.items() if d and "change_pct" in d and d["change_pct"] >= 0]
    down = [(n, d["change_pct"]) for n, d in indices.items() if d and "change_pct" in d and d["change_pct"] < 0]

    sp500 = indices.get("S&P 500", {})
    nasdaq = indices.get("Nasdaq", {})
    dow = indices.get("Dow Jones", {})
    russell = indices.get("Russell 2000", {})
    vix = vix_data.get("price") if vix_data else None
    vix_c = vix_data.get("change_pct") if vix_data else None

    paragraphs = []

    tone_parts = []
    if up and not down:
        avg_up = sum(p for _, p in up) / len(up)
        if avg_up > 1.5:
            tone_parts.append(f"Markets opened with conviction this morning, with all major indices charging higher. The broad-based rally averaged {avg_up:.1f}%, reflecting optimistic sentiment.")
        elif avg_up > 0.5:
            tone_parts.append(f"Equities traded in positive territory across the board, with the major indices posting a steady climb. The average gain of {avg_up:.1f}% suggests measured optimism.")
        else:
            tone_parts.append(f"Markets edged higher in quiet trading, with all major indices finishing in the green. Gains were modest at an average of {avg_up:.1f}%.")
    elif down and not up:
        avg_down = sum(p for _, p in down) / len(down)
        if avg_down < -1.5:
            tone_parts.append(f"Selling pressure dominated as all major indices retreated, averaging {avg_down:.1f}%.")
        else:
            tone_parts.append(f"Markets traded lower across the board, averaging {avg_down:.1f}%.")
    else:
        leaders = sorted(up, key=lambda x: -x[1])[:2]
        laggards = sorted(down, key=lambda x: x[1])[:2]
        tone_parts.append("Markets were mixed this morning with clear divergence.")
        if leaders:
            tone_parts[-1] += " " + " and ".join([f"{n} ({p:+.1f}%)" for n, p in leaders]) + " led the upside."
        if laggards:
            tone_parts[-1] += " " + " and ".join([f"{n} ({p:+.1f}%)" for n, p in laggards]) + " lagged."
    paragraphs.append(" ".join(tone_parts))

    detail = []
    if sp500 and "price" in sp500:
        detail.append(f"S&P 500 at {sp500['price']:,.0f} ({sp500.get('change_pct',0):+.2f}%).")
    if nasdaq and "price" in nasdaq:
        nq = nasdaq["price"]
        nq_c = nasdaq.get("change_pct", 0)
        suffix = ""
        if sectors:
            tech = sectors.get("Tech (XLK)", {})
            if tech and tech.get("change_pct", 0) > 0.5:
                suffix = " (tech-led)"
        detail.append(f"Nasdaq at {nq:,.0f} ({nq_c:+.2f}%{suffix}).")
    if dow and "price" in dow:
        detail.append(f"Dow at {dow['price']:,.0f} ({dow.get('change_pct',0):+.2f}%).")
    if russell and "price" in russell:
        rt_c = russell.get("change_pct", 0)
        note = "outperforming" if rt_c > 0.5 else "underperforming" if rt_c < -0.5 else "in line"
        detail.append(f"Russell 2000 at {russell['price']:,.0f} ({rt_c:+.2f}%, {note} large caps).")
    paragraphs.append(" ".join(detail))

    context = []
    if vix:
        v = float(vix)
        if v < 14:
            context.append(f"VIX at {v:.1f} — remarkably subdued, investors see no near-term turbulence.")
        elif v < 18:
            context.append(f"VIX at {v:.1f} — complacent market, no acute stress signals.")
        elif v < 25:
            context.append(f"VIX at {v:.1f} — modest anxiety, investors eyeing downside risks.")
        else:
            context.append(f"VIX at {v:.1f} — elevated fear, hedging activity picking up.")
        if vix_c and abs(vix_c) > 5:
            context[-1] = context[-1].rstrip(".") + f", {'spiking' if vix_c > 0 else 'falling'} {abs(vix_c):.0f}% from prior session."
    if context:
        paragraphs.append(" ".join(context))

    synthesis = []
    gold = commodities.get("Gold", {})
    oil = commodities.get("Crude Oil", {})
    if gold and oil and gold.get("change_pct", 0) > 0 and oil.get("change_pct", 0) > 0:
        synthesis.append("Both gold and crude rose — unusual combo suggesting broad commodity demand rather than a pure safe-haven or growth narrative.")
    usd_dir = _usd_direction(forex)
    if usd_dir == "weaker":
        synthesis.append("A weaker dollar is providing tailwinds for equities and commodities alike.")
    if synthesis:
        paragraphs.append(" ".join(synthesis))

    if recs and recs.get("buys"):
        top = recs["buys"][:3]
        pick_str = ", ".join([f"{p['ticker']} (${p['price']:.1f}, {p['change_pct']:+.1f}%)" for p in top])
        paragraphs.append(f"Top stock picks this morning: {pick_str}. These names show the strongest combination of technical momentum and value signals.")

    forward = []
    if sp500 and sp500.get("ytd_change_pct", 0) and abs(sp500["ytd_change_pct"]) > 3:
        ytd = sp500["ytd_change_pct"]
        forward.append(f"Over the trailing 30 days, the S&P 500 is {abs(ytd):.1f}% {'above' if ytd > 0 else 'below'} its level a month ago{' — a notable move traders will watch for confirmation' if abs(ytd) > 5 else '.'}")
    if forward:
        paragraphs.append(" ".join(forward))

    return {"title": "AI Market Overview", "body": "\n\n".join(paragraphs)}


def _stock_picks(recs):
    if not recs or not recs.get("buys"):
        return None

    buys = recs["buys"][:5]
    lines = []
    for p in buys:
        arrow = "▲" if p["change_pct"] >= 0 else "▼"
        lines.append(f"{p['ticker']} at ${p['price']:.2f} ({arrow}{p['change_pct']:+.2f}%) — RSI {p['rsi']:.0f}, {p['reasons']}.")

    parts = [
        f"Based on technical analysis of {len(buys)} qualifying names, the strongest BUY signals are:",
        " " + " ".join(lines),
        "These recommendations combine RSI momentum, moving average positioning, and volume confirmation. Always perform your own due diligence before trading."
    ]

    if recs.get("watches"):
        watch = recs["watches"][:3]
        watch_str = ", ".join([f"{w['ticker']} (RSI {w['rsi']:.0f})" for w in watch])
        parts.append(f"On the watch list (potential reversals): {watch_str}.")

    return {"title": "Stock Picks", "body": " ".join(parts)}


def _usd_direction(forex):
    if not forex:
        return "neutral"
    s, c = 0, 0
    for n, d in forex.items():
        if d and "change_pct" in d:
            s += -d["change_pct"]
            c += 1
    if c == 0:
        return "neutral"
    a = s / c
    return "stronger" if a > 0.2 else "weaker" if a < -0.2 else "mixed"


def _sector_analysis(sectors):
    if not sectors:
        return None
    ranked = [(n, d["change_pct"]) for n, d in sectors.items() if d and "change_pct" in d]
    if not ranked:
        return None
    ranked.sort(key=lambda x: -x[1])
    top, bottom = ranked[0], ranked[-1]
    spread = top[1] - bottom[1]
    up_count = sum(1 for _, p in ranked if p > 0)
    total = len(ranked)

    parts = [
        f"Leading: {top[0]} ({top[1]:+.1f}%). Lagging: {bottom[0]} ({bottom[1]:+.1f}%).",
    ]
    if spread > 5:
        parts.append(f"Wide {spread:.1f}% dispersion — stock-picker's market.")
    elif spread > 2:
        parts.append(f"{spread:.1f}% spread suggests moderate sector rotation.")
    else:
        parts.append(f"Tight {spread:.1f}% spread — broad market forces driving price action.")

    if up_count == total:
        parts.append("All sectors positive — broad buying.")
    elif up_count >= total * 0.6:
        parts.append(f"{up_count}/{total} sectors green — bullish internals.")
    elif up_count >= total * 0.3:
        parts.append(f"Only {up_count}/{total} sectors green — selective market.")
    else:
        parts.append(f"Just {up_count}/{total} sectors positive — defensive positioning.")

    return {"title": "Sector Analysis", "body": " ".join(parts)}


def _commodities_insight(commodities):
    if not commodities:
        return None
    parts = []
    gold = commodities.get("Gold", {})
    oil = commodities.get("Crude Oil", {})
    silver = commodities.get("Silver", {})
    natgas = commodities.get("Natural Gas", {})

    if gold and "price" in gold:
        gc = gold["change_pct"]
        if gc > 0.5:
            parts.append(f"Gold rising {gc:+.1f}% to ${gold['price']:,.0f}/oz.")
            if gc > 1.5:
                parts.append("Notable move — possibly geopolitical or real rate driven.")
        elif gc < -0.5:
            parts.append(f"Gold slipping {gc:+.1f}% to ${gold['price']:,.0f}.")
        else:
            parts.append(f"Gold flat at ${gold['price']:,.0f}.")

    if oil and "price" in oil:
        oc = oil["change_pct"]
        if oc > 1:
            parts.append(f"Crude surging {oc:+.1f}% to ${oil['price']:.2f}.")
        elif oc > 0:
            parts.append(f"Crude up {oc:+.1f}% to ${oil['price']:.2f}.")
        elif oc < -1:
            parts.append(f"Crude dropping {oc:+.1f}% to ${oil['price']:.2f}.")
        else:
            parts.append(f"Crude flat at ${oil['price']:.2f}.")

    if silver and abs(silver.get("change_pct", 0)) > 1.5:
        parts.append(f"Silver moved {silver['change_pct']:+.1f}%.")
    if natgas and abs(natgas.get("change_pct", 0)) > 2:
        parts.append(f"Natural gas volatile at {natgas['change_pct']:+.1f}%.")

    if not parts:
        return None
    return {"title": "Commodities Brief", "body": " ".join(parts)}


def _forex_insight(forex):
    if not forex:
        return None
    s, c = 0, 0
    pairs_data = []
    for n, d in forex.items():
        if d and "change_pct" in d:
            s += -d["change_pct"]
            c += 1
            pairs_data.append((n, d["change_pct"]))
    if c == 0:
        return None
    avg = s / c
    notable = [(n, p) for n, p in pairs_data if abs(p) > 0.4]

    if avg > 0.3:
        note = f"Dollar strengthening {avg:.1f}% vs majors."
    elif avg > 0.1:
        note = f"Dollar modestly firmer ({avg:.1f}%)."
    elif avg < -0.3:
        note = f"Dollar under pressure ({abs(avg):.1f}%)."
    elif avg < -0.1:
        note = f"Dollar slightly softer ({abs(avg):.1f}%)."
    else:
        note = "Dollar mixed vs majors."
    parts = [note]
    if notable:
        strs = []
        for n, p in sorted(notable, key=lambda x: -abs(x[1])):
            d = "strengthening" if p > 0 else "weakening"
            strs.append(f"{n.replace('/','')} {d} ({p:+.1f}%)")
        parts.append(" " + ". ".join(strs) + ".")
    return {"title": "FX Overview", "body": "".join(parts)}


def _macro_context(indices, vix_data):
    sp500 = indices.get("S&P 500", {})
    if not sp500 or "ytd_change_pct" not in sp500:
        return None
    ytd = sp500["ytd_change_pct"]
    vix = vix_data.get("price") if vix_data else None
    vix_c = vix_data.get("change_pct") if vix_data else None
    parts = []
    d = "above" if ytd > 0 else "below"
    s = "comfortably" if abs(ytd) > 5 else "modestly" if abs(ytd) > 2 else "marginally"
    parts.append(f"S&P 500 sits {s} {d} its 30-day level ({ytd:+.1f}%).")
    if vix:
        v = float(vix)
        if v < 14 and ytd > 0:
            parts.append(f"Low VIX ({v:.1f}) confirms low-stress bull environment.")
        elif v > 22 and ytd < 0:
            parts.append(f"Elevated VIX ({v:.1f}) aligns with negative equity trend.")
        if vix_c and abs(vix_c) > 8:
            parts.append(f"VIX {'jumped' if vix_c > 0 else 'dropped'} {vix_c:+.0f}% — notable shift.")
    return {"title": "Macro Context", "body": " ".join(parts)}
