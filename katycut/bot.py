import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import database
from config import TELEGRAM_BOT_TOKEN
from handlers import easter_egg, payment, photo, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    # Validate config
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "REPLACE_ME":
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

    # Init DB
    await database.init_db()

    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register routers in priority order
    # easter_egg and payment must come before text to catch specific triggers
    dp.include_router(easter_egg.router)
    dp.include_router(payment.router)
    dp.include_router(photo.router)
    dp.include_router(text.router)

    logger.info("KatyCut bot starting...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await database.close_pool()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
