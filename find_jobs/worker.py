import nest_asyncio
nest_asyncio.apply()
from config.config import load_config
from db.db import init_db
from scheduler.scheduler import start_scheduler, cleanup_scheduler
import asyncio

if __name__ == "__main__":
    config = load_config()
    init_db(config)
    bot, scheduler = start_scheduler(config)
    try:
        print('Worker running. Press Ctrl+C to exit.')
        print('Scheduler will automatically run job_scrape_and_alert every 30 minutes.')
        
        # Let the scheduler handle the scraping automatically
        # Don't manually trigger job_scrape_and_alert here
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Worker shutting down...")
    finally:
        cleanup_scheduler(scheduler) 