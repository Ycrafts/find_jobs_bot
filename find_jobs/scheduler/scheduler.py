from apscheduler.schedulers.background import BackgroundScheduler
from scraper.scraper import scrape_jobs, cleanup_pyrogram_client
from db.db import save_job_post, fetch_all_users, mark_jobs_as_sent, fetch_unsent_jobs_for_user
import logging
from telegram import Bot
import requests
import asyncio
from typing import List, Dict, Any, Tuple

# Send job alert to user
def send_job_alert(bot, user_id, jobs, config=None):
    if not jobs:
        return
    text = 'New job matches for you:\n'
    for job in jobs:
        text += f"\n{job.get('title', 'Job')} at {job.get('company', '')}\n{job.get('url', '')}\n"
    if config is not None:
        token = config['TELEGRAM_BOT_TOKEN']
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": user_id, "text": text}
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")


def _format_jobs_for_log(scored: List[Tuple[Dict[str, Any], float]]):
    return [
        {"title": j.get('title'), "score": round(s, 3), "url": j.get('url')}
        for j, s in scored
    ]


class JobScheduler:
    def __init__(self):
        pass

    def run_scrape_and_alert(self, config, bot):
        try:
            logging.info('Running scheduled job scrape and alert')
            jobs = scrape_jobs(config)
            for job in jobs:
                save_job_post(job)
            users = fetch_all_users()
            from matching.ai_matcher import get_ai_matcher, select_top_matches
            ai_matcher = get_ai_matcher(config)
            min_score = float(config.get('AI_MIN_SCORE', 0.5))
            top_k = int(config.get('AI_TOP_K', 5))
            for user in users:
                candidate_jobs = fetch_unsent_jobs_for_user(user['user_id'])
                scored = ai_matcher.score_jobs(user, candidate_jobs)
                top_matches_scored = select_top_matches(scored, top_k=top_k, min_score=min_score)
                top_jobs_only = [job for job, score in top_matches_scored]
                send_job_alert(bot, user['user_id'], top_jobs_only, config)
                mark_jobs_as_sent(user['user_id'], top_jobs_only)
        except Exception as e:
            print(f"Exception in job_scrape_and_alert: {e}")

    def start(self, config):
        scheduler = BackgroundScheduler()
        bot = Bot(token=config['TELEGRAM_BOT_TOKEN'])
        scheduler.add_job(lambda: self.run_scrape_and_alert(config, bot), 'interval', minutes=config['JOB_SCRAPE_INTERVAL_MINUTES'])
        scheduler.start()
        return bot, scheduler

    def cleanup(self, scheduler):
        try:
            scheduler.shutdown(wait=False)
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    loop.create_task(cleanup_pyrogram_client())
                else:
                    pass
            except RuntimeError:
                try:
                    asyncio.run(cleanup_pyrogram_client())
                except RuntimeError:
                    pass
                except Exception as e:
                    print(f"Error during Pyrogram cleanup: {e}")
            except Exception as e:
                print(f"Error during Pyrogram cleanup: {e}")
        except Exception as e:
            print(f"Error during scheduler cleanup: {e}")


_job_scheduler_singleton = JobScheduler()


def job_scrape_and_alert(config, bot):
    return _job_scheduler_singleton.run_scrape_and_alert(config, bot)


def start_scheduler(config):
    return _job_scheduler_singleton.start(config)


def cleanup_scheduler(scheduler):
    return _job_scheduler_singleton.cleanup(scheduler) 