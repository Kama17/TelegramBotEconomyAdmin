import asyncio
from bot.economyAdminClient import MyBot
from db_handler.db_handler import DatabaseHandler
from config.setup import AIP_HASH, AIP_TOKEN

async def main():
    allowed_chat_ids = [-1002243654237]  # Replace with your allowed chat IDs
    db_handler = DatabaseHandler()
    my_bot = MyBot(api_id=27642056, api_hash=AIP_HASH, api_token=AIP_TOKEN, db_handler=db_handler, allowed_chat_ids=allowed_chat_ids)
    await my_bot.run()

if __name__ == '__main__':
    asyncio.run(main())