from pyrogram import Client
import re
import asyncio
import nest_asyncio
import threading

# Optional: ensure TgCrypto is importable so Pyrogram can use it if present
try:
    import tgcrypto  # noqa: F401
    tgcrypto_available = True
except Exception:
    tgcrypto_available = False

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Global client instance to reuse
_pyrogram_client = None
_client_lock = threading.Lock()

# TODO: Add your Telegram API credentials in config


def parse_job_from_message(message, channel_username, config=None):
    text = message.text or getattr(message, 'caption', None) or ""
    # Normalize and split lines
    raw_lines = text.split('\n')
    lines = [ln.strip() for ln in raw_lines if ln.strip()]

    title = lines[0] if lines else "Job Post"

    # Initialize defaults
    company = ''
    location = ''
    field = ''
    experience = ''
    description_lines = []

    # Regex for labeled fields like: Company: X, Location: Y, Field: Z, Experience: W, Description: ...
    label_re = re.compile(r'^(Company|Location|Field|Experience|Description)\s*:\s*(.+)$', re.IGNORECASE)

    # Parse remaining lines for labels; if not a labeled line, collect into description
    for ln in lines[1:]:
        m = label_re.match(ln)
        if m:
            key = m.group(1).lower()
            value = m.group(2).strip()
            if key == 'company':
                company = value
            elif key == 'location':
                location = value
            elif key == 'field':
                field = value
            elif key == 'experience':
                experience = value
            elif key == 'description':
                description_lines.append(value)
        else:
            description_lines.append(ln)

    description = '\n'.join(description_lines).strip()

    # AI-based enrichment to fill missing fields best-effort
    try:
        if config is not None and any(v == '' for v in (company, location, field, experience)):
            from matching.ai_extractor import extract_fields
            ai_out = extract_fields(text, config)
            if company == '' and 'company' in ai_out:
                company = ai_out['company']
            if location == '' and 'location' in ai_out:
                location = ai_out['location']
            if field == '' and 'field' in ai_out:
                field = ai_out['field']
            if experience == '' and 'experience' in ai_out:
                experience = ai_out['experience']
    except Exception as e:
        # Best-effort only; ignore enrichment failures
        pass

    channel_name = channel_username.lstrip('@')
    url = f"https://t.me/{channel_name}/{message.id}"
    return {
        'title': title,
        'company': company,
        'location': location,
        'field': field,
        'experience': experience,
        'description': description,
        'url': url,
    }


class TelegramScraper:
    def __init__(self):
        pass

    async def get_pyrogram_client(self, config):
        global _pyrogram_client
        with _client_lock:
            if _pyrogram_client is None:
                api_id = int(config['PYROGRAM_API_ID'])
                api_hash = config['PYROGRAM_API_HASH']
                session_string = config.get('PYROGRAM_SESSION_STRING')
                _pyrogram_client = Client(
                    session_string,
                    api_id=api_id,
                    api_hash=api_hash,
                    session_string=session_string,
                    no_updates=True
                )
                # Log whether TgCrypto is available (Pyrogram prefers it automatically)
                if tgcrypto_available:
                    print("Pyrogram: TgCrypto detected and will be used for MTProto.")
                else:
                    print("Pyrogram: TgCrypto not detected; falling back to pure-Python crypto.")
                await _pyrogram_client.start()
        return _pyrogram_client

    async def async_scrape_telegram_channels(self, config, channels):
        jobs = []
        try:
            app = await self.get_pyrogram_client(config)
            for channel in channels:
                try:
                    async for message in app.get_chat_history(channel, limit=20):
                        # Consider both text messages and media with captions
                        if getattr(message, 'text', None) or getattr(message, 'caption', None):
                            job = parse_job_from_message(message, channel, config)
                            jobs.append(job)
                except Exception as e:
                    print(f"Failed to scrape channel {channel}: {e}")
                    continue
        except Exception as e:
            print(f"Failed to initialize Pyrogram client: {e}")
            return []
        return jobs

    def scrape_telegram_channels(self, config, channels):
        try:
            return asyncio.run(self.async_scrape_telegram_channels(config, channels))
        except Exception as e:
            print(f"Failed to scrape Telegram channels: {e}")
            return []

    async def cleanup_pyrogram_client(self):
        global _pyrogram_client
        with _client_lock:
            if _pyrogram_client:
                try:
                    if _pyrogram_client.is_connected:
                        await _pyrogram_client.stop()
                    else:
                        pass
                except Exception as e:
                    print(f"Error stopping Pyrogram client: {e}")
                finally:
                    _pyrogram_client = None


def get_pyrogram_client(config):
    return asyncio.run(TelegramScraper().get_pyrogram_client(config))


def async_scrape_telegram_channels(config, channels):
    return TelegramScraper().async_scrape_telegram_channels(config, channels)


def scrape_telegram_channels(config, channels):
    return TelegramScraper().scrape_telegram_channels(config, channels)


def scrape_jobs(config):
    channels = config.get('TELEGRAM_CHANNELS') or []
    if not channels:
        print("No TELEGRAM_CHANNELS configured; skipping scrape.")
        return []
    return TelegramScraper().scrape_telegram_channels(config, channels)


async def cleanup_pyrogram_client():
    return await TelegramScraper().cleanup_pyrogram_client() 