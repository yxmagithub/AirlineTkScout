# Flight Ticket Price Monitor

A Python tool that monitors flight prices via the **Amadeus API** and sends alerts when prices drop below your target or fall by a configurable percentage. Supports flexible **date ranges**, **stop filters**, **Gmail**, **Telegram**, and **console** notifications.

## Features

- Monitor multiple routes simultaneously
- **Flexible date ranges** — search a window of departure and return dates; automatically finds the cheapest date combination
- **Stop filter** — limit to non-stop only (`max_stops: 0`) or max 1 connection (`max_stops: 1`)
- Alert when price drops below a fixed threshold
- Alert when price drops by a configurable percentage vs. the last check
- 24-hour alert cooldown to avoid notification spam (re-alerts immediately if price drops another 5%)
- Price history stored in SQLite — tracks which dates gave the best price
- Configurable check interval (default: every 60 minutes)
- `--once` flag to run a single check and exit (great for cron jobs)

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/AirlineTkPVT_IAT.git
cd AirlineTkPVT_IAT
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get an Amadeus API key

1. Sign up at [developers.amadeus.com](https://developers.amadeus.com)
2. Create a new app — you'll receive a **Client ID** and **Client Secret**
3. The free sandbox gives realistic test data for most major routes

### 4. Configure credentials

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

**.env fields:**

| Variable | Required | Description |
|---|---|---|
| `AMADEUS_CLIENT_ID` | Yes | Amadeus API client ID |
| `AMADEUS_CLIENT_SECRET` | Yes | Amadeus API client secret |
| `AMADEUS_ENV` | No | `test` (sandbox) or `production` (default: `test`) |
| `GMAIL_ADDRESS` | No | Your Gmail address for sending alerts |
| `GMAIL_APP_PASSWORD` | No | Gmail [App Password](https://support.google.com/accounts/answer/185833) (not your regular password) |
| `ALERT_EMAIL_TO` | No | Recipient email (defaults to `GMAIL_ADDRESS`) |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token from [@BotFather](https://t.me/botfather) |
| `TELEGRAM_CHAT_ID` | No | Your Telegram chat ID (send `/start` to [@userinfobot](https://t.me/userinfobot)) |

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
      max_price: 400           # alert if price < this (null to disable)
      drop_percent: 10         # alert if price drops by this % (null to disable)

  # Fixed date example
  - name: "Chicago to Miami"
    origin: ORD
    destination: MIA
    departure_date: "2026-12-20"
    return_date: null          # null or omit for one-way
    adults: 2
    cabin: ECONOMY
    currency: USD
    max_stops: 1
    alert:
      max_price: 250
      drop_percent: 15
```

Use [IATA airport codes](https://www.iata.org/en/publications/directories/code-search/).

### 6. Run

```bash
# Continuous loop (checks every N minutes as configured)
python main.py

# Single check and exit
python main.py --once
```

## Project Structure

```
├── main.py              # Entry point and scheduler loop
├── monitor.py           # Core price-check and alert logic
├── amadeus_client.py    # Amadeus API wrapper (date ranges, stop filtering)
├── price_tracker.py     # SQLite price history and alert log
├── config.py            # Environment variable loading
├── routes.yaml          # Route and alert configuration
├── notifiers/
│   ├── base.py          # Abstract base notifier + message formatter
│   ├── console_notifier.py
│   ├── email_notifier.py
│   └── telegram_notifier.py
├── .env.example         # Credential template
└── requirements.txt
```

## Alert Example

```
============================================================
Flight Price Alert: New York to Los Angeles (Flexible)
Route  : JFK → LAX
Dates  : 2026-07-12 → 2026-07-22  (searched 2026-07-10 – 2026-07-20, return 2026-07-22 – 2026-07-30)
Cabin  : ECONOMY  |  Adults: 1
Price  : USD 319.40  (AA, 1 stop(s))
Reason : - price USD 319.40 is below your target of USD 400.00
         - price dropped 12.3% (was USD 364.10, now USD 319.40)
============================================================
```

## API Call Budget

With date ranges, each `(departure_date, return_date)` pair requires one Amadeus API call.

| Config | Departure dates | Return dates | Calls/check |
|---|---|---|---|
| Fixed dates | 1 | 1 | 1 |
| 10-day range, step 2 | 5 | — | 5 |
| 10-day dep + 8-day ret, step 2 | 5 | 4 | up to 20 |

The Amadeus **free sandbox** has no hard call limit. The **production free tier** allows 2,000 calls/month. Increase `step_days` to reduce call volume.

## Notes

- **Sandbox vs Production**: The Amadeus sandbox returns realistic but not live prices. Set `AMADEUS_ENV=production` once your app is approved by Amadeus.
- **Gmail App Password**: Required if your Gmail account has 2-Step Verification (recommended). Regular passwords won't work.
- **Stop filter**: `max_stops: 0` passes `nonStop=true` to the API. `max_stops: 1` fetches more results and post-filters — slightly more API response data but still one call per date pair.

## License

MIT
