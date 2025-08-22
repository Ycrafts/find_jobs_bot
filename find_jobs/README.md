# Find Jobs Telegram Bot

A modular Telegram bot that helps Ethiopian job seekers find relevant jobs based on their profile. It scrapes job sites and Telegram channels, matches jobs to users, and sends alerts.

## Features

- User profile collection (/start)
- Supabase PostgreSQL storage
- Scrapes ethiojobs.net, employethiopia.com, Telegram job channels
- AI-based job matching (provider-agnostic; default: Hugging Face zero-shot)
- Sends job alerts via Telegram
- Easy deployment (Docker, Render/Railway)

## Structure

```
bot/         # Telegram bot logic
scraper/     # Job scraping logic
scheduler/   # Periodic job matching and alert sending
db/          # Supabase database interaction
config/      # Config and environment
matching/    # AI-based matching providers and helpers
main.py      # Entrypoint
```

## Setup

1. Copy `.env.example` to `.env` and fill in your secrets.
2. Install requirements: `pip install -r requirements.txt`
3. Run: `python main.py`

### Environment variables

- `TELEGRAM_BOT_TOKEN`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `PYROGRAM_API_ID`
- `PYROGRAM_API_HASH`
- `PYROGRAM_SESSION_STRING`
- `JOB_SCRAPE_INTERVAL_MINUTES` (default 30)
- `TELEGRAM_CHANNELS` (REQUIRED) JSON array or comma-separated
  - Examples:
    - JSON: `["@channel_one", "@channel_two"]`
    - CSV: `@channel_one,@channel_two`
- `AI_MATCH_PROVIDER` (default `huggingface_zeroshot`)
- `HF_API_KEY` (required for Hugging Face provider)
- `AI_MODEL_ID` (default `facebook/bart-large-mnli`)
- `AI_MIN_SCORE` (default `0.5`)
- `AI_TOP_K` (default `5`)

## Deployment

- Use Dockerfile and render.yaml/railway.json for cloud deployment.
