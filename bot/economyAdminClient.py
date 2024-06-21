from telethon import TelegramClient, events
from telegram import Bot as TelegramBot, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackContext, CommandHandler
from telethon.tl.types import ChannelParticipantsAdmins
import asyncio
from datetime import datetime, timedelta
import aiojobs
from telegram import Bot

from logger_handler.logger_config import setup_logger
from config.setup import HK_CHAT_ID, BOT_CHAT_ID

logger = setup_logger()

class MyBot:
    def __init__(self, api_id, api_hash, api_token, db_handler, allowed_chat_ids):
        self.api_id = api_id
        self.api_hash = api_hash
        self.api_token = api_token
        self.db_handler = db_handler
        self.allowed_chat_ids = allowed_chat_ids
        self.bot = TelegramClient('bot', api_id, api_hash)
        self.telegram_bot = TelegramBot(token=api_token)
        self.application = ApplicationBuilder().token(api_token).build()


    async def get_users_on_start_up(self):

        all_users = await self.bot.get_participants(HK_CHAT_ID)
        admins = await self.bot.get_participants(HK_CHAT_ID, filter=ChannelParticipantsAdmins)

        # Create a set of admin IDs for faster lookup
        admin_ids = {admin.id for admin in admins}

        # Filter out users who are admins
        users_only = [user for user in all_users if user.id not in admin_ids]
        self.db_handler.add_chat_users(users_only, HK_CHAT_ID)

    async def start(self):
        await self.bot.start(bot_token=self.api_token)
        self.bot.add_event_handler(self.handle_add_joined_member, events.ChatAction)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.telegram_handler))
        self.bot.add_event_handler(self.handle_user_update, events.UserUpdate)
        #await self.get_users_on_start_up() #Sheduld user update in the case user changes his username
        invalid_user_names, banned_users = self.db_handler.enrollment_renewals()

        if invalid_user_names:
            for user in invalid_user_names:
                print("invalid_user_names", invalid_user_names)
                await self.bot.send_message(BOT_CHAT_ID, f"User name does't include Economy ID: {user[3]}")

        if banned_users:
            for user in banned_users:
                    await self.bot.send_message(BOT_CHAT_ID, f"User name {user[6]} didn't renew membership, id: {user[3]}")
        logger.info("Bot started")

    async def handle_user_update(self, event):
        user = await self.client.get_entity(event.user_i)
        self.db_handler.add_member(event.chat_id, user.id,  user.access_hash, None, user.first_name, user.last_name, user.username)

    async def handle_add_joined_member(self, event):
        if event.chat_id in self.allowed_chat_ids:
            if event.user_added or event.user_joined:
                for user in event.users:
                    print(f"Users joined:{user}")
                    self.db_handler.add_member(event.chat_id, user.id,  user.access_hash, None, user.first_name, user.last_name, user.username)
                    logger.info(f"User {user.id} added to chat {event.chat_id} User Name: {user.username}")

    async def telegram_handler(self, update, context: CallbackContext):
        if update.message.chat_id in self.allowed_chat_ids:
            await update.message.reply_text('Hello, this is a restricted bot!')
            logger.info(f"Message from allowed chat: {update.message.text}")

    async def monitor(self):
        await self.bot.run_until_disconnected()
        logger.info("Monitoring new members")

    async def scheduled_task(self):
        logger.info("Scheduled task is running")
        print("Scheduled task is running")
        self.db_handler.enrollment_renewals()
        # Add your scheduled task code here

    async def schedule_daily_task(self, scheduler, task, hour, minute):
        while True:
            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if now > target_time:
                target_time += timedelta(days=1)
            wait_time = (target_time - now).total_seconds()
            await asyncio.sleep(wait_time)
            await scheduler.spawn(task())

    async def run(self):
        try:
            await self.start()
            scheduler = await aiojobs.create_scheduler()
            daily_task = asyncio.create_task(self.schedule_daily_task(scheduler, self.scheduled_task, hour=13, minute=45))
            monitor_task = asyncio.create_task(self.monitor())
            await asyncio.gather(monitor_task, daily_task)
        except Exception as e:
            logger.error("An error occurred", exc_info=True)
        finally:
            self.db_handler.close()
