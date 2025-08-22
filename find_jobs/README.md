# Find Jobs – Telegram Bot

A production-ready Telegram bot that helps job seekers get relevant job alerts. It scrapes Telegram job channels, enriches and stores posts, matches them to user profiles using an AI model, and sends personalized alerts.

## Features

- **Onboarding flow**: collects location, profession, experience, and work preference
- **Free‑text profession**: when “Other” is chosen, user can type a custom field
- **Location guidance**: clear instructions to enable device location when required
- **Scraping**: pulls recent posts from configured Telegram channels via Pyrogram
- **AI enrichment**: fills missing fields (company/location/field/experience) best‑effort
- **AI matching**: zero‑shot classification (Hugging Face) to score job relevance
- **Storage**: Supabase (PostgreSQL) for users, jobs, and sent alerts
- **Scheduling**: APScheduler runs recurring scrape → match → alert cycles
- **Alerts**: sends top matches to each user via Telegram Bot API
- **Containerized**: Dockerfile, docker‑compose; `APP_MODE` supports main/worker/all

## Repo structure

```
bot/         # Telegram bot conversation and commands
scraper/     # Telegram channels scraper (Pyrogram)
scheduler/   # APScheduler wrapper and job pipeline
matching/    # AI extractor and matcher (Hugging Face APIs)
db/          # Supabase repository and helpers
config/      # Env and config loader
main.py      # Entrypoint to run the bot (optionally one-off scrape)
worker.py    # Entrypoint for the scheduler in a separate process
entrypoint.py# Orchestrates both processes in Docker when APP_MODE=all
```

## Architecture overview

1. User starts the bot (/start), shares location, selects or types profession, picks experience and preference.
2. Scheduler periodically:
   - Scrapes configured Telegram channels
   - Parses posts and AI‑enriches missing fields
   - Stores deduplicated jobs in Supabase
   - Scores jobs for each user and sends top matches, marking them as sent

## Prerequisites

- Python 3.11+ or Docker
- Telegram Bot token
- Supabase project (URL + service role key)
- Pyrogram credentials (API ID, API HASH) and a session string
- Hugging Face API key (for AI extraction and matching)

## Environment variables

The app reads variables via `dotenv` and process env. Key variables:

- `TELEGRAM_BOT_TOKEN` – Telegram bot token
- `SUPABASE_URL` – Supabase URL
- `SUPABASE_KEY` – Supabase service role key
- `PYROGRAM_API_ID` – Telegram API ID
- `PYROGRAM_API_HASH` – Telegram API hash
- `PYROGRAM_SESSION_STRING` – Pyrogram session string
- `JOB_SCRAPE_INTERVAL_MINUTES` – scrape interval (default: 30)
- `TELEGRAM_CHANNELS` – JSON array or CSV of channels
  - JSON example: `@["@channel_one", "@channel_two"]`
  - CSV example: `@channel_one,@channel_two`
- `AI_MATCH_PROVIDER` – default `huggingface_zeroshot`
- `HF_API_KEY` – Hugging Face Inference API key
- `AI_MODEL_ID` – default `facebook/bart-large-mnli`
- `AI_MIN_SCORE` – filter threshold for matches (default: `0.5`)
- `AI_TOP_K` – top K matches to send (default: `5`)
- `ENABLE_SCHEDULER` – set `true/false` in `main.py` mode (Docker runs both by default)
- `APP_MODE` – Docker only: `main`, `worker`, or `all` (default `all`)

Create `find_jobs/.env` for Docker compose (or export env vars locally):

```env
TELEGRAM_BOT_TOKEN=...
SUPABASE_URL=...
SUPABASE_KEY=...
PYROGRAM_API_ID=...
PYROGRAM_API_HASH=...
PYROGRAM_SESSION_STRING=...
TELEGRAM_CHANNELS=["@channel_one", "@channel_two"]
HF_API_KEY=...
AI_MIN_SCORE=0.5
AI_TOP_K=5
JOB_SCRAPE_INTERVAL_MINUTES=30
```

## Local development (Python)

```bash
# from find_jobs/ directory
pip install -r requirements.txt
python main.py
```

- Press Ctrl+C to stop. `main.py` runs the bot and can do a one‑off scrape if `ENABLE_SCHEDULER=true`.
- To run the recurring scheduler locally, use:

```bash
python worker.py
```

## Local development (Docker)

Build and run with compose (recommended):

```bash
# from repo root
cd find_jobs
docker build -t find-jobs:latest -f Dockerfile .
cd ..
docker compose up --build
```

Run modes (single container):

```bash
# Bot only
docker run --rm --env-file .\find_jobs\.env -e APP_MODE=main find-jobs:latest

# Scheduler only
docker run --rm --env-file .\find_jobs\.env -e APP_MODE=worker find-jobs:latest

# Both (default)
docker run --rm --env-file .\find_jobs\.env -e APP_MODE=all find-jobs:latest
```

## Generating a Pyrogram session string

You need a valid session string to allow the scraper to read channel history.

- Option A: Use the provided helper if available in your workspace
  (adjust as needed):

```bash
python generate_session.py
```

- Option B: Follow Pyrogram docs to log in and print a session string.

Set the result as `PYROGRAM_SESSION_STRING` in your env.

## Database schema (Supabase)

Expected tables:

- `users` – columns: `user_id (bigint)`, `location (jsonb)`, `profession (text)`, `experience (text)`, `preferences (text)`
- `jobs` – columns: `id (bigint, pk/identity)`, `title (text)`, `company (text)`, `location (text)`, `field (text)`, `experience (text)`, `description (text)`, `url (text, unique)`
- `sent_alerts` – columns: `user_id (bigint)`, `job_id (bigint)`

Create unique index on `jobs.url` to dedupe posts.

## Using the bot

- `/start` – begins profile setup
  - Prompts to enable device location and share it
  - Choose a profession or pick “Other” to type your own
  - Select experience level and work preference
- `/update` – re‑runs the profile setup to change details
- `/cancel` – cancels current flow

## Configuration tips

- Set `AI_MIN_SCORE` higher to send fewer but stronger matches
- Increase `AI_TOP_K` to send more results per cycle
- Tune `JOB_SCRAPE_INTERVAL_MINUTES` to control scraping frequency

## Deployment

- Dockerfile is production‑ready; `entrypoint.py` manages both processes with graceful shutdown.
- `render.yaml` example provided; set environment variables in your hosting platform.

## Troubleshooting

- Bot not responding:
  - Verify `TELEGRAM_BOT_TOKEN` and that the bot is started in Telegram
- No jobs scraped:
  - Ensure `TELEGRAM_CHANNELS` is set; session string and API credentials are valid
- No alerts sent:
  - Make sure users completed onboarding; check `HF_API_KEY` and logs for AI calls
- Docker build issues:
  - Rebuild with no cache: `docker compose build --no-cache`

## License

MIT
