import os
import json
import glob
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, jsonify, abort, request
from briefing import load_latest_briefing, list_briefings, load_briefing, DATA_DIR, generate_briefing
from db import init_db, add_subscriber, remove_subscriber, get_active_subscribers, get_subscriber_by_token, subscriber_count
from notify import send_briefing_to_subscribers, build_html_email, build_text_summary
from config import TRIGGER_SECRET
from predictor import fetch_stock, generate_signal, predict_targets, generate_insight

app = Flask(__name__)

init_db()


def get_shared_context():
    b = load_latest_briefing()
    today = datetime.now(timezone(timedelta(hours=-4))).strftime("%A, %B %d, %Y")
    if not b or b.get("date") != today:
        b = generate_briefing()
    return {"subscriber_count": subscriber_count(), "briefing": b}


@app.route("/")
def overview():
    ctx = get_shared_context()
    b = ctx["briefing"]
    ai_overview = None
    if b and b.get("insights"):
        for s in b["insights"]:
            if s["title"] == "AI Market Overview":
                ai_overview = s
                break
    ctx["ai_overview"] = ai_overview
    ctx["active_page"] = "overview"
    return render_template("overview.html", **ctx)


@app.route("/news")
def news():
    ctx = get_shared_context()
    ctx["active_page"] = "news"
    return render_template("news.html", **ctx)


@app.route("/picks")
def picks():
    ctx = get_shared_context()
    ctx["active_page"] = "picks"
    return render_template("picks.html", **ctx)


@app.route("/predictions")
def predictions():
    ctx = get_shared_context()
    b = ctx["briefing"]
    sections = {}
    if b and b.get("insights"):
        for s in b["insights"]:
            sections[s["title"]] = s
    ctx["sections"] = sections
    ctx["active_page"] = "predictions"
    return render_template("predictions.html", **ctx)


@app.route("/insights")
def insights():
    ctx = get_shared_context()
    b = ctx["briefing"]
    other = []
    if b and b.get("insights"):
        other = [s for s in b["insights"] if s["title"] != "AI Market Overview"]
    ctx["other_insights"] = other
    ctx["active_page"] = "insights"
    return render_template("insights.html", **ctx)


@app.route("/data")
def data_view():
    ctx = get_shared_context()
    ctx["active_page"] = "data"
    return render_template("data.html", **ctx)


@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    ctx = get_shared_context()
    ctx["active_page"] = "subscribe"

    if request.method == "GET":
        return render_template("signup.html", **ctx, flash=None)

    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    carrier = request.form.get("carrier", "").strip()

    if not email or "@" not in email:
        return render_template("signup.html", **ctx, flash={"category": "error", "message": "Please enter a valid email address."})

    row = add_subscriber(email, phone, carrier)
    if row:
        return render_template("signup.html", **ctx, flash={"category": "success", "message": "You're subscribed! You'll receive the daily briefing each morning."})
    else:
        return render_template("signup.html", **ctx, flash={"category": "error", "message": "This email is already subscribed."})


@app.route("/unsubscribe/<token>")
def unsubscribe(token):
    sub = get_subscriber_by_token(token)
    if sub:
        remove_subscriber(token)
        return render_template("unsubscribed.html", message=f"{sub['email']} has been unsubscribed.")
    return render_template("unsubscribed.html", message="Invalid or expired unsubscribe link.")


@app.route("/trigger", methods=["POST"])
def trigger_briefing():
    secret = request.headers.get("X-Trigger-Secret", "")
    if secret != TRIGGER_SECRET:
        abort(401)

    briefing = generate_briefing()
    html = build_html_email(briefing)
    text = build_text_summary(briefing)
    results = send_briefing_to_subscribers(html, text)
    return jsonify({"status": "ok", "sent": results})


@app.route("/api/latest")
def api_latest():
    briefing = load_latest_briefing()
    if not briefing:
        return jsonify({"error": "No briefing data yet"}), 404
    return jsonify(briefing)


@app.route("/api/briefings")
def api_briefings():
    files = list_briefings()
    result = []
    for f in files:
        b = load_briefing(f)
        if b:
            result.append({"filename": f, "date": b.get("date", f)})
    return jsonify(result)


@app.route("/api/subscribers/count")
def api_subscriber_count():
    return jsonify({"count": subscriber_count()})


@app.route("/api/stock/<ticker>")
def api_stock(ticker):
    data = fetch_stock(ticker)
    if not data:
        return jsonify({"error": "Ticker not found"}), 404
    signal, score, reasons = generate_signal(data)
    targets = predict_targets(data)
    insight = generate_insight(data, signal, targets)
    return jsonify({
        "ticker": data["ticker"],
        "name": data["name"],
        "price": data["price"],
        "change": data["change"],
        "change_pct": data["change_pct"],
        "signal": signal,
        "score": score,
        "reasons": reasons,
        "rsi": data["rsi_14"],
        "sma_20": data["sma_20"],
        "above_sma": data["above_sma"],
        "volume_ratio": data["volume_ratio"],
        "momentum_5d": data["momentum_5d"],
        "targets": targets,
        "insight": insight,
    })


@app.route("/search", methods=["GET", "POST"])
def search():
    ctx = get_shared_context()
    ctx["active_page"] = "search"
    result = None
    error = None
    if request.method == "POST":
        ticker = request.form.get("ticker", "").strip().upper()
        if ticker:
            data = fetch_stock(ticker)
            if data:
                signal, score, reasons = generate_signal(data)
                targets = predict_targets(data)
                insight = generate_insight(data, signal, targets)
                result = {
                    "data": data,
                    "signal": signal,
                    "score": score,
                    "reasons": reasons,
                    "targets": targets,
                    "insight": insight,
                }
            else:
                error = f"Could not find data for ticker '{ticker}'."
        else:
            error = "Please enter a ticker symbol."
    ctx["result"] = result
    ctx["error"] = error
    return render_template("search.html", **ctx)


@app.route("/history")
def history():
    ctx = get_shared_context()
    files = list_briefings()
    briefings = []
    for f in files:
        b = load_briefing(f)
        if b:
            briefings.append({"filename": f, "date": b.get("date", f)})
    ctx["briefings"] = briefings
    ctx["active_page"] = "history"
    return render_template("history.html", **ctx)


@app.route("/briefing/<filename>")
def view_briefing(filename):
    if not filename.endswith(".json"):
        filename += ".json"
    b = load_briefing(filename)
    if not b:
        abort(404)
    ctx = get_shared_context()
    ctx["briefing"] = b
    ai_overview = None
    if b.get("insights"):
        for s in b["insights"]:
            if s["title"] == "AI Market Overview":
                ai_overview = s
                break
    ctx["ai_overview"] = ai_overview
    return render_template("overview.html", **ctx)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
