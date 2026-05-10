import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from briefing import generate_briefing, load_latest_briefing
from config import EMAIL, CARRIER_GATEWAYS
from db import get_active_subscribers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DASHBOARD_URL = os.environ.get("WEB_APP_URL", "https://your-app.onrender.com")


def build_html_email(briefing):
    headlines = briefing.get("headlines", [])
    insights = briefing.get("insights", [])
    market_data = briefing.get("market_data", {})
    date_str = briefing.get("date", datetime.now(timezone(timedelta(hours=-4))).strftime("%A, %B %d, %Y"))
    dashboard_link = os.environ.get("DASHBOARD_URL", DASHBOARD_URL)

    news_html = ""
    for h in headlines[:5]:
        news_html += f"""
    <div style="padding:12px 0;border-bottom:1px solid #1e293b;">
        <a href="{h['link']}" style="color:#e2e8f0;text-decoration:none;font-size:14px;line-height:1.4;display:block;">{h['title']}</a>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">{h['source']}</div>
    </div>"""

    insights_html = ""
    for item in insights[:4]:
        insights_html += f"""
    <div style="margin-bottom:12px;">
        <div style="font-size:11px;color:#60a5fa;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">{item['title']}</div>
        <div style="font-size:13px;color:#cbd5e1;line-height:1.5;">{item['body']}</div>
    </div>"""

    table_rows = ""
    for category in ("US Indices", "Forex", "Commodities", "Sectors"):
        items = market_data.get(category, {})
        if not items:
            continue
        table_rows += f'<tr><td colspan="4" style="padding:12px 0 4px;font-size:11px;color:#38bdf8;text-transform:uppercase;letter-spacing:0.05em;border:none;">{category}</td></tr>'
        for name, data in items.items():
            if not data or "price" not in data:
                continue
            change = data.get("change_pct", 0)
            arrow = "▲" if change >= 0 else "▼"
            color = "#22c55e" if change >= 0 else "#ef4444"
            table_rows += f"""<tr>
                <td style="padding:6px 8px;font-size:13px;border-bottom:1px solid #1e293b;">{name}</td>
                <td style="padding:6px 8px;font-size:13px;font-family:'SF Mono','Fira Code',monospace;border-bottom:1px solid #1e293b;">{data.get('price', 'N/A')}</td>
                <td style="padding:6px 8px;font-size:13px;font-family:'SF Mono','Fira Code',monospace;font-weight:600;color:{color};border-bottom:1px solid #1e293b;">{arrow} {change:+.2f}%</td>
                <td style="padding:6px 8px;font-size:13px;font-family:'SF Mono','Fira Code',monospace;font-weight:600;color:{color};border-bottom:1px solid #1e293b;">{data.get('change', 0):+.2f}</td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; margin:0; padding:0; background:#0f172a; color:#e2e8f0; }}
</style></head>
<body style="background:#0f172a;color:#e2e8f0;padding:24px;">
<div style="max-width:580px;margin:0 auto;">

    <div style="border-bottom:1px solid #334155;padding-bottom:16px;margin-bottom:24px;">
        <div style="font-size:20px;font-weight:600;color:#f8fafc;">Market Briefing</div>
        <div style="font-size:12px;color:#94a3b8;">{date_str}</div>
    </div>

    {news_html}

    <div style="border-top:1px solid #334155;margin-top:20px;padding-top:20px;margin-bottom:24px;">
        {insights_html}
    </div>

    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
        <tr><th style="text-align:left;padding:6px 8px;font-size:10px;text-transform:uppercase;color:#64748b;border-bottom:1px solid #334155;">Name</th>
        <th style="text-align:left;padding:6px 8px;font-size:10px;text-transform:uppercase;color:#64748b;border-bottom:1px solid #334155;">Price</th>
        <th style="text-align:left;padding:6px 8px;font-size:10px;text-transform:uppercase;color:#64748b;border-bottom:1px solid #334155;">%</th>
        <th style="text-align:left;padding:6px 8px;font-size:10px;text-transform:uppercase;color:#64748b;border-bottom:1px solid #334155;">Chg</th></tr>
        {table_rows}
    </table>

    <div style="font-size:11px;color:#475569;border-top:1px solid #334155;padding-top:16px;">
        <a href="{{unsubscribe_link}}" style="color:#475569;text-decoration:none;">Unsubscribe</a>
        &nbsp;·&nbsp;
        <a href="{dashboard_link}" style="color:#60a5fa;text-decoration:none;">View full dashboard</a>
    </div>

</div>
</body>
</html>"""
    return html


def build_text_summary(briefing):
    headlines = briefing.get("headlines", [])
    insights = briefing.get("insights", [])
    date_str = briefing.get("date", "")

    parts = [f"MARKET BRIEFING — {date_str}", ""]

    if headlines:
        parts.append("HEADLINES")
        for h in headlines[:3]:
            parts.append(f"  • {h['title']}")
        parts.append("")

    if insights:
        for item in insights[:3]:
            parts.append(f"{item['title']}: {item['body']}")
        parts.append("")

    market_data = briefing.get("market_data", {})
    parts.append("PRICE DATA")
    for category in ("US Indices", "Forex", "Commodities"):
        items = market_data.get(category, {})
        for name, data in items.items():
            if not data or "price" not in data:
                continue
            change = data.get("change_pct", 0)
            arrow = "+" if change >= 0 else ""
            parts.append(f"  {name}: {data['price']}  ({arrow}{change:.2f}%)")
    parts.append("")
    parts.append(f"Full dashboard: {DASHBOARD_URL}")
    return "\n".join(parts)


def send_email(to_addr, html_body, text_body, subject=None):
    if EMAIL["from"] == "your.email@gmail.com" or EMAIL["password"] == "your-app-password":
        logging.warning("Email not configured. Set EMAIL in config.py")
        return False

    if not subject:
        today = datetime.now().strftime("%b %d, %Y")
        subject = f"Market Briefing — {today}"

    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL["from"]
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(EMAIL["smtp_server"], EMAIL["smtp_port"])
        server.starttls()
        server.login(EMAIL["from"], EMAIL["password"])
        server.sendmail(EMAIL["from"], [to_addr], msg.as_string())
        server.quit()
        logging.info(f"Email sent to {to_addr}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to_addr}: {e}")
        return False


def send_sms(to_addr, text_body):
    if EMAIL["from"] == "your.email@gmail.com" or EMAIL["password"] == "your-app-password":
        return False

    msg = MIMEText(text_body, "plain")
    msg["From"] = EMAIL["from"]
    msg["To"] = to_addr
    msg["Subject"] = "Market Briefing"

    try:
        server = smtplib.SMTP(EMAIL["smtp_server"], EMAIL["smtp_port"])
        server.starttls()
        server.login(EMAIL["from"], EMAIL["password"])
        server.sendmail(EMAIL["from"], [to_addr], msg.as_string())
        server.quit()
        logging.info(f"SMS sent to {to_addr}")
        return True
    except Exception as e:
        logging.error(f"Failed to send SMS to {to_addr}: {e}")
        return False


def send_briefing_to_subscribers(html, text):
    subscribers = get_active_subscribers()
    results = {"email": 0, "sms": 0, "failed": 0}

    for sub in subscribers:
        unsubscribe_link = f"{DASHBOARD_URL}/unsubscribe/{sub['unsubscribe_token']}"
        email_body = html.replace("{{unsubscribe_link}}", unsubscribe_link)
        ok = send_email(sub["email"], email_body, text)
        if ok:
            results["email"] += 1
        else:
            results["failed"] += 1

        if sub.get("phone") and sub.get("carrier"):
            gateway = CARRIER_GATEWAYS.get(sub["carrier"])
            if gateway:
                sms_addr = f"{sub['phone']}@{gateway}"
                ok = send_sms(sms_addr, text)
                if ok:
                    results["sms"] += 1
                else:
                    results["failed"] += 1

    logging.info(f"Sent to {results['email']} emails, {results['sms']} SMS, {results['failed']} failed")
    return results


def send_briefing():
    briefing = generate_briefing()
    html = build_html_email(briefing)
    text = build_text_summary(briefing)
    return send_briefing_to_subscribers(html, text)


if __name__ == "__main__":
    send_briefing()
