from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler)
from db.db import save_user_profile, get_user_profile
import logging

# States for conversation
(ASK_LOCATION, ASK_PROFESSION, ASK_EXPERIENCE, ASK_PREFERENCES, ASK_PROFESSION_OTHER) = range(5)

user_profiles = {}  # Temporary in-memory storage for conversation


class TelegramBotService:
    def __init__(self, config):
        self.config = config
        self.application = None

    def build_application(self):
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("telegram_bot")

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            logger.info(f"/start invoked by user_id={user_id}")
            existing_profile = get_user_profile(user_id)
            if existing_profile:
                logger.info(f"User {user_id} has existing profile; ending conversation")
                await update.message.reply_text(
                    f"Welcome back! Your profile is already set up:\n"
                    f"📍 Location: {existing_profile['location']['lat']:.4f}, {existing_profile['location']['lon']:.4f}\n"
                    f"💼 Profession: {existing_profile['profession']}\n"
                    f"📊 Experience: {existing_profile['experience']}\n"
                    f"🎯 Preferences: {existing_profile['preferences']}\n\n"
                    f"You'll receive job alerts automatically. Use /update to modify your profile.",
                    reply_markup=ReplyKeyboardRemove()
                )
                return ConversationHandler.END
            else:
                logger.info(f"Starting onboarding for user {user_id}: asking for location")
                await update.message.reply_text(
                    "Welcome! Before we start, please turn on your device location services (GPS).\n"
                    "Then share your location using the button below.",
                    reply_markup=ReplyKeyboardMarkup(
                        [[KeyboardButton("Share Location", request_location=True)]],
                        one_time_keyboard=True, resize_keyboard=True
                    )
                )
                return ASK_LOCATION

        async def update_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            logger.info(f"/update invoked by user_id={user_id}")
            existing_profile = get_user_profile(user_id)
            if not existing_profile:
                logger.info(f"User {user_id} has no profile; instructing to /start")
                await update.message.reply_text("You don't have a profile yet. Use /start to create one.")
                return ConversationHandler.END
            logger.info(f"User {user_id}: requesting new location for update")
            await update.message.reply_text(
                "Let's update your profile. Please make sure location services are turned ON,\n"
                "then share your new location:",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("Share Location", request_location=True)]],
                    one_time_keyboard=True, resize_keyboard=True
                )
            )
            return ASK_LOCATION

        async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            loc = update.message.location
            if not loc:
                logger.info(f"User {user_id} did not provide location; prompting again")
                await update.message.reply_text(
                    "Please turn ON location services (GPS) and use the button to share your location.",
                    reply_markup=ReplyKeyboardMarkup(
                        [[KeyboardButton("Share Location", request_location=True)]],
                        one_time_keyboard=True, resize_keyboard=True
                    )
                )
                return ASK_LOCATION
            logger.info(f"User {user_id} shared location lat={loc.latitude}, lon={loc.longitude}")
            user_profiles[user_id] = {'user_id': user_id, 'location': {'lat': loc.latitude, 'lon': loc.longitude}}
            
            profession_keyboard = [
                [InlineKeyboardButton("💻 Software Engineering", callback_data="profession_software")],
                [InlineKeyboardButton("📊 Data Science", callback_data="profession_data")],
                [InlineKeyboardButton("🎨 UI/UX Design", callback_data="profession_design")],
                [InlineKeyboardButton("📱 Mobile Development", callback_data="profession_mobile")],
                [InlineKeyboardButton("🌐 Web Development", callback_data="profession_web")],
                [InlineKeyboardButton("🔧 DevOps", callback_data="profession_devops")],
                [InlineKeyboardButton("📈 Product Management", callback_data="profession_product")],
                [InlineKeyboardButton("📝 Content Writing", callback_data="profession_content")],
                [InlineKeyboardButton("🎯 Marketing", callback_data="profession_marketing")],
                [InlineKeyboardButton("📋 Other (type your own)", callback_data="profession_other")]
            ]
            
            await update.message.reply_text(
                "Great! Now choose your profession or field:",
                reply_markup=InlineKeyboardMarkup(profession_keyboard)
            )
            return ASK_PROFESSION

        async def profession_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            user_id = update.effective_user.id
            profession_map = {
                "profession_software": "Software Engineering",
                "profession_data": "Data Science", 
                "profession_design": "UI/UX Design",
                "profession_mobile": "Mobile Development",
                "profession_web": "Web Development",
                "profession_devops": "DevOps",
                "profession_product": "Product Management",
                "profession_content": "Content Writing",
                "profession_marketing": "Marketing",
            }
            if query.data == "profession_other":
                await query.edit_message_text(
                    "Please type your profession or field (e.g., 'Embedded Systems Engineer')."
                )
                return ASK_PROFESSION_OTHER
            chosen = profession_map.get(query.data)
            if not chosen:
                chosen = "Other"
            user_profiles[user_id]['profession'] = chosen
            logger.info(f"User {user_id} selected profession='{chosen}'")
            
            experience_keyboard = [
                [InlineKeyboardButton("🆕 Entry Level", callback_data="experience_entry")],
                [InlineKeyboardButton("👨‍💼 Mid Level", callback_data="experience_mid")],
                [InlineKeyboardButton("👨‍💻 Senior Level", callback_data="experience_senior")],
                [InlineKeyboardButton("🎯 Lead/Manager", callback_data="experience_lead")]
            ]
            
            await query.edit_message_text(
                f"Selected: {user_profiles[user_id]['profession']}\n\nNow choose your experience level:",
                reply_markup=InlineKeyboardMarkup(experience_keyboard)
            )
            return ASK_EXPERIENCE

        async def profession_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            text = (update.message.text or '').strip()
            if not text:
                await update.message.reply_text("Please enter a valid profession (text).")
                return ASK_PROFESSION_OTHER
            user_profiles[user_id]['profession'] = text[:100]
            logger.info(f"User {user_id} entered custom profession='{text}'")
            
            experience_keyboard = [
                [InlineKeyboardButton("🆕 Entry Level", callback_data="experience_entry")],
                [InlineKeyboardButton("👨‍💼 Mid Level", callback_data="experience_mid")],
                [InlineKeyboardButton("👨‍💻 Senior Level", callback_data="experience_senior")],
                [InlineKeyboardButton("🎯 Lead/Manager", callback_data="experience_lead")]
            ]
            await update.message.reply_text(
                f"Selected: {user_profiles[user_id]['profession']}\n\nNow choose your experience level:",
                reply_markup=InlineKeyboardMarkup(experience_keyboard)
            )
            return ASK_EXPERIENCE

        async def experience_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            user_id = update.effective_user.id
            experience_map = {
                "experience_entry": "Entry Level",
                "experience_mid": "Mid Level",
                "experience_senior": "Senior Level", 
                "experience_lead": "Lead/Manager"
            }
            chosen = experience_map.get(query.data, "Mid Level")
            user_profiles[user_id]['experience'] = chosen
            logger.info(f"User {user_id} selected experience='{chosen}'")
            
            preferences_keyboard = [
                [InlineKeyboardButton("🏠 Remote Only", callback_data="preferences_remote")],
                [InlineKeyboardButton("🏢 Onsite Only", callback_data="preferences_onsite")],
                [InlineKeyboardButton("🔄 Hybrid", callback_data="preferences_hybrid")],
                [InlineKeyboardButton("✅ Any (Remote/Onsite)", callback_data="preferences_any")]
            ]
            
            await query.edit_message_text(
                f"Selected: {user_profiles[user_id]['experience']}\n\nFinally, choose your work preferences:",
                reply_markup=InlineKeyboardMarkup(preferences_keyboard)
            )
            return ASK_PREFERENCES

        async def preferences_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            user_id = update.effective_user.id
            preferences_map = {
                "preferences_remote": "Remote Only",
                "preferences_onsite": "Onsite Only", 
                "preferences_hybrid": "Hybrid",
                "preferences_any": "Any (Remote/Onsite)"
            }
            chosen = preferences_map.get(query.data, "Any (Remote/Onsite)")
            user_profiles[user_id]['preferences'] = chosen
            
            save_user_profile(user_profiles[user_id])
            logger.info(f"User {user_id} saved profile: profession='{user_profiles[user_id]['profession']}', experience='{user_profiles[user_id]['experience']}', preferences='{chosen}'")
            
            profile = user_profiles[user_id]
            await query.edit_message_text(
                f"🎉 Profile Setup Complete!\n\n"
                f"📍 Location: {profile['location']['lat']:.4f}, {profile['location']['lon']:.4f}\n"
                f"💼 Profession: {profile['profession']}\n"
                f"📊 Experience: {profile['experience']}\n"
                f"🎯 Preferences: {profile['preferences']}\n\n"
                f"✅ Your profile has been saved! You'll receive job alerts soon."
            )
            return ConversationHandler.END

        async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"User {update.effective_user.id} cancelled profile setup")
            await update.message.reply_text(
                "Profile setup cancelled.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        application = ApplicationBuilder().token(self.config['TELEGRAM_BOT_TOKEN']).build()
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start), CommandHandler('update', update_profile)],
            states={
                ASK_LOCATION: [MessageHandler(filters.LOCATION, location)],
                ASK_PROFESSION: [CallbackQueryHandler(profession_callback, pattern='^profession_')],
                ASK_PROFESSION_OTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, profession_text_handler)],
                ASK_EXPERIENCE: [CallbackQueryHandler(experience_callback, pattern='^experience_')],
                ASK_PREFERENCES: [CallbackQueryHandler(preferences_callback, pattern='^preferences_')],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        application.add_handler(conv_handler)
        self.application = application
        return application

    def run(self):
        if self.application is None:
            self.build_application()
        try:
            print("Bot started successfully!")
            # Lower timeout so long-poll exits within ~1s on Ctrl+C
            self.application.run_polling(drop_pending_updates=True, close_loop=False, timeout=1.0)
        except KeyboardInterrupt:
            print("Bot shutdown requested...")
        except Exception as e:
            print(f"Bot error: {e}")
        finally:
            print("Bot cleanup completed.") 


def start_bot(config):
    service = TelegramBotService(config)
    service.build_application()
    service.run() 