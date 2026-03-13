import logging

from aiogram import Router, F
from aiogram.types import Message, FSInputFile

import database
from config import EASTER_EGG_GATS_IMAGE

logger = logging.getLogger(__name__)
router = Router()

# From n8n Switch1: text contains "Гатс"
EASTER_EGG_WORDS = {"гатс", "guts", "gatz", "gats"}


@router.message(F.text.func(lambda t: t and any(w in t.lower() for w in EASTER_EGG_WORDS)))
async def handle_easter_egg(message: Message):
    user = message.from_user
    db_user = await database.get_or_create_user(tg_id=user.id, username=user.username)

    already_seen = db_user.get("easter_egg1", False)
    if not already_seen:
        await database.set_easter_egg1(user.id)

    # From n8n: Send a photo message1 caption
    await message.answer_photo(
        photo=FSInputFile(EASTER_EGG_GATS_IMAGE),
        caption=(
            "Упс! Меня поймали.\n\n"
            "Что вершит судьбу человечества в этом мире? Да хрен его знает!\n"
            "Зато ты знаешь, кто лучше всех вырезает. ✂️\n\n"
            "P.S. пришли эту картинку в тг-канал моему создателю и получишь бонус"
        ),
    )
    logger.info(f"Easter egg triggered by user {user.id}")
