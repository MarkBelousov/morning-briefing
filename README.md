# Morning Market Briefing Agent

Automated daily market briefing — emails a summary and hosts a web dashboard.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure email

Edit `config.py`:

```python
EMAIL = {
    "from": "your.email@gmail.com",
    "password": "your-gmail-app-password",  # Generate at https://myaccount.google.com/apppasswords
    "to": ["your.email@gmail.com"],
}
```

For SMS, add entries to `SMS`:

```python
SMS = {
    "1234567890@vtext.com": "Verizon",  # See config.py for carrier gateways
}
```

### 3. Run locally

```bash
python3 briefing.py      # generate briefing data
python3 notify.py        # send email/SMS
```

### 4. Run the web app

```bash
python3 app.py
# Visit http://localhost:5000
```

## Deploy

### GitHub Actions (daily schedule)

1. Push this repo to GitHub
2. Add repository secrets:
   - `EMAIL_FROM` — your Gmail address
   - `EMAIL_PASSWORD` — Gmail app password
   - `EMAIL_TO` — comma-separated recipients
   - `SMS_TO` — JSON dict `{"number@gateway": "Carrier"}`
3. The workflow runs weekdays at 7:30 AM ET (11:30 UTC)

### Web App (Render)

1. Create a new **Web Service** on Render
2. Connect your GitHub repo
3. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Deploy

## Project Structure

```
morning-briefing/
├── config.py              Settings (tickers, email, SMS)
├── fetcher.py             Market data via yfinance
├── headlines.py           RSS news aggregation
├── briefing.py            Generate briefing JSON
├── notify.py              Email + SMS delivery
├── app.py                 Flask web dashboard
├── templates/             HTML templates
├── data/                  Generated briefing files
├── .github/workflows/    GitHub Actions cron job
├── requirements.txt
└── run.sh                 Local run script
```
