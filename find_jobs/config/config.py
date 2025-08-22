import os
from dotenv import load_dotenv
import json

# Load .env from the current working directory
load_dotenv()


def _parse_channels_env(raw_value: str):
    if not raw_value:
        return []
    raw_value = raw_value.strip()
    # Try JSON array first
    if raw_value.startswith('['):
        try:
            data = json.loads(raw_value)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except Exception:
            pass
    # Fallback: comma-separated
    parts = [p.strip() for p in raw_value.split(',') if p.strip()]
    return parts


def _parse_bool(raw_value: str, default: bool) -> bool:
    if raw_value is None:
        return default
    val = str(raw_value).strip().lower()
    if val in ("1", "true", "yes", "on"):  # enable
        return True
    if val in ("0", "false", "no", "off"):  # disable
        return False
    return default


def load_config():
    return {
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_KEY': os.getenv('SUPABASE_KEY'),
        'PYROGRAM_API_ID': os.getenv('PYROGRAM_API_ID'),
        'PYROGRAM_API_HASH': os.getenv('PYROGRAM_API_HASH'),
        'PYROGRAM_SESSION_STRING': os.getenv('PYROGRAM_SESSION_STRING'),
        'JOB_SCRAPE_INTERVAL_MINUTES': float(os.getenv('JOB_SCRAPE_INTERVAL_MINUTES', 30)),
        # AI matching configuration (provider-agnostic)
        'AI_MATCH_PROVIDER': os.getenv('AI_MATCH_PROVIDER', 'huggingface_zeroshot'),
        'HF_API_KEY': os.getenv('HF_API_KEY'),
        'AI_MODEL_ID': os.getenv('AI_MODEL_ID', 'facebook/bart-large-mnli'),
        'AI_MIN_SCORE': float(os.getenv('AI_MIN_SCORE', 0.5)),
        'AI_TOP_K': int(os.getenv('AI_TOP_K', 5)),
        # Telegram channels to scrape (JSON array or comma-separated)
        'TELEGRAM_CHANNELS': _parse_channels_env(os.getenv('TELEGRAM_CHANNELS', '')),
        # Control whether main.py starts the scheduler (set to false when running worker.py separately)
        'ENABLE_SCHEDULER': _parse_bool(os.getenv('ENABLE_SCHEDULER', 'true'), True),
    } 