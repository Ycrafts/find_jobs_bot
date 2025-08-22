import os
import nest_asyncio
import signal
import sys
nest_asyncio.apply()
from config.config import load_config
from bot.bot import start_bot
from scheduler.scheduler import start_scheduler, job_scrape_and_alert, cleanup_scheduler
from db.db import init_db


if __name__ == "__main__":
	config = load_config()
	init_db(config)

	scheduler = None
	if config.get('ENABLE_SCHEDULER', True):
		bot, scheduler = start_scheduler(config)
	else:
		print("ENABLE_SCHEDULER is false: running bot only (no scheduler in main.py)")
	
	try:
		# One-off run for initial scrape and alert cycle only if scheduler enabled
		if scheduler is not None:
			job_scrape_and_alert(config, bot)
		print("Starting bot... Press Ctrl+C to exit gracefully.")
		start_bot(config)
	except KeyboardInterrupt:
		print("\nShutting down gracefully...")
	except Exception as e:
		print(f"Error during execution: {e}")
	finally:    
		print("Cleaning up resources...")
		try:
			if scheduler is not None:
				cleanup_scheduler(scheduler)
			print("Cleanup completed successfully!")
		except Exception as e:
			print(f"Error during cleanup: {e}")
		print("Shutdown complete.") 