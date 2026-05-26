# AirlineTkScout — Flight Ticket Price Monitor

A Python tool that monitors flight prices via **Google Flights (SerpAPI)** and sends alerts when prices drop below your target or fall by a configurable percentage. Supports flexible **date ranges**, **stop filters**, **Gmail**, **Telegram**, and **console** notifications.

## Features

- Real Google Flights prices via SerpAPI
- Monitor multiple routes simultaneously
- **Top 3 most competitive options** shown in every alert (price, airline, stops, dates)
- **Flexible date ranges** — search a window of departure and return dates; finds the cheapest date combination automatically
- **Stop filter** — non-stop only (`max_stops: 0`) or max 1 connection (`max_stops: 1`)
- Alert when price drops below a fixed threshold
- Alert when price drops by a configurable percentage vs. the last check
- 24-hour alert cooldown (re-alerts immediately if price drops another 5%)
- Price history stored in SQLite
- Configurable check interval (default: every 60 minutes)
- `--once` flag for a single check (great for cron jobs)

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/yxmagithub/AirlineTkScout.git
cd AirlineTkScout
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get a SerpAPI key

1. Sign up at [serpapi.com](https://serpapi.com) — **100 free searches/month** included
2. Copy your API key from the dashboard

### 4. Configure credentials

```bash
cp .env.example .env
# Edit .env with your actual values
```

**.env fields:**

| Variable | Required | Description |
|---|---|---|
| `SERPAPI_KEY` | Yes | SerpAPI key |
| `GMAIL_ADDRESS` | No | Gmail address for sending alerts |
| `GMAIL_APP_PASSWORD` | No | Gmail [App Password](https://support.google.com/accounts/answer/185833) |
| `ALERT_EMAIL_TO` | No | Recipient email (defaults to `GMAIL_ADDRESS`) |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token from [@BotFather](https://t.me/botfather) |
| `TELEGRAM_CHAT_ID` | No | Your Telegram chat ID (from [@userinfobot](https://t.me/userinfobot)) |

Gmail and Telegram are **optional** — the tool always logs to console and `monitor.log`.

### 5. Configure routes

Edit `routes.yaml`:

```yaml
check_interval_minutes: 60

routes:
  # Flexible date range example
  - name: "New York to Los Angeles (Flexible)"
    origin: JFK
    destination: LAX
    departure_date_range:
      from: "2026-07-10"
      to: "2026-07-20"
      step_days: 2             # check every 2nd day (reduces API calls)
    return_date_range:
      from: "2026-07-22"
      to: "2026-07-30"
      step_days: 2
    trip_length_days:          # only consider trips of 5-10 nights
      min: 5
      max: 10
    adults: 1
    cabin: ECONOMY             # ECONOMY | PREMIUM_ECONOMY | BUSINESS | FIRST
    currency: USD
    max_stops: 1               # 0 = non-stop only | 1 = max 1 connection | null = no filter
    alert:
      max_price: 400           # alert if cheapest price < this (null to disable)
      drop_percent: 10         # alert if price drops by this % (null to disable)

  # Fixed date example
  - name: "Chicago to Miami"
    origin: ORD
    destination: MIA
    departure_date: "2026-12-20"
    return_date: null
    adults: 2
    cabin: ECONOMY
    currency: USD
    max_stops: 1
    alert:
      max_price: 250
      drop_percent: 15
```

### 6. Run

```bash
# Continuous loop
python main.py

# Single check and exit
python main.py --once
```

## Alert Example

```
============================================================
Flight Price Alert: New York to Los Angeles (Flexible)
Route   : JFK → LAX
Dates   : searched 2026-07-10 – 2026-07-20, return 2026-07-22 – 2026-07-30
Cabin   : ECONOMY  |  Adults: 1

Top 3 Most Competitive Options:
  #1  USD 319.40  |  American Airlines  |  non-stop   |  2026-07-12 → 2026-07-22
  #2  USD 334.20  |  Delta              |  1 stop(s)  |  2026-07-14 → 2026-07-24
  #3  USD 352.80  |  United             |  1 stop(s)  |  2026-07-10 → 2026-07-22

Alert   : - cheapest price USD 319.40 is below your target of USD 400.00
          - price dropped 12.3% (was USD 364.10, now USD 319.40)
============================================================
```

## Project Structure

```
├── main.py              # Entry point and scheduler loop
├── monitor.py           # Core price-check and alert logic
├── flight_client.py     # Google Flights client via SerpAPI
├── price_tracker.py     # SQLite price history and alert log
├── config.py            # Environment variable loading
├── routes.yaml          # Route and alert configuration
├── notifiers/
│   ├── base.py          # Abstract base + message formatter
│   ├── console_notifier.py
│   ├── email_notifier.py
│   └── telegram_notifier.py
├── .env.example         # Credential template
└── requirements.txt
```

## API Call Budget

SerpAPI free tier: **100 searches/month**.

| Config | Calls per check cycle |
|---|---|
| 1 fixed-date route | 1 |
| 1 route, 10-day dep range (step 2) | 5 |
| 1 route, dep + ret range (step 2 each) | up to 25 |

With a 60-minute interval and 1 fixed route, that's ~720 calls/month — upgrade to the $50/mo plan (5,000 searches) for heavier monitoring.

## Notes

- **Gmail App Password**: Required if your Gmail has 2-Step Verification. Regular passwords won't work.
- **Stop filter**: `max_stops: 0` passes `stops=1` (nonstop only) to SerpAPI. `max_stops: 1` passes `stops=2` (1 stop or fewer).

## License

MIT
