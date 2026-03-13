import asyncio
import io
import logging

from aiogram import Router, Bot, F
from aiogram import Bot as AiogramBot
from aiogram.types import Message, BufferedInputFile, FSInputFile

import database
from config import (
    ADMIN_TG_ID,
    ADMIN_USER_IDS,
    CONGRATS_5_GEN_IMAGE,
    CONGRATS_10_GEN_IMAGE,
    NOTIFY_BOT_TOKEN,
)
from services.fal_ai import remove_background
from services.openai_service import get_funny_comment

logger = logging.getLogger(__name__)
router = Router()

SUPPORTED_MIME_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp",
    "image/gif", "image/bmp", "image/tiff",
}


async def _check_and_deduct_token(user_id: int) -> tuple[bool, str]:
    if user_id in ADMIN_USER_IDS:
        return True, ""

    if await database.can_use_free(user_id):
        await database.use_free_token(user_id)
        return True, "free"

    paid = await database.get_paid_tokens(user_id)
    if paid > 0:
        await database.deduct_paid_token(user_id)
        return True, "paid"

    return False, "no_tokens"


async def _get_image_bytes(message: Message, bot: Bot) -> tuple[bytes, str]:
    if message.photo:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        bio = io.BytesIO()
        await bot.download_file(file.file_path, destination=bio)
        return bio.getvalue(), "photo.jpg"

    if message.document:
        doc = message.document
        mime = (doc.mime_type or "").lower()
        if mime not in SUPPORTED_MIME_TYPES and not mime.startswith("image/"):
            raise ValueError(f"Unsupported file type: {doc.mime_type}")
        file = await bot.get_file(doc.file_id)
        bio = io.BytesIO()
        await bot.download_file(file.file_path, destination=bio)
        return bio.getvalue(), doc.file_name or "image.jpg"

    raise ValueError("No photo or document in message")


async def process_photo(message: Message, bot: Bot):
    user = message.from_user
    await database.get_or_create_user(tg_id=user.id, username=user.username)

    can_proceed, reason = await _check_and_deduct_token(user.id)
    if not can_proceed:
        await message.answer(
            "Упс! Закончились вырезки 😢\n\n"
            "1 бесплатная вырезка в день уже использована.\n"
            "Купи пакет токенов — напиши /buy или «купить» ✂️💜"
        )
        return

    status_msg = None

    try:
        image_bytes, filename = await _get_image_bytes(message, bot)

        # Run GPT comment + FAL.ai in parallel
        comment_task = asyncio.create_task(get_funny_comment(image_bytes, filename))
        fal_task = asyncio.create_task(remove_background(image_bytes, filename))

        comment = await comment_task
        status_msg = await message.answer(f"{comment}\nСейчас вырежу")

        result_bytes = await fal_task

        base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
        output_filename = f"{base_name}_no_bg.png"

        await message.answer_document(
            document=BufferedInputFile(result_bytes, filename=output_filename),
        )

        try:
            await status_msg.delete()
        except Exception:
            pass

        new_total = await database.increment_total_generations(user.id)
        await _send_milestone_congrats(message, new_total)

        try:
            notify_bot = AiogramBot(token=NOTIFY_BOT_TOKEN)
            await notify_bot.send_message(ADMIN_TG_ID, "+1 Катя отработала")
            await notify_bot.session.close()
        except Exception:
            pass

    except ValueError as e:
        err_text = "Этот формат не поддерживается 😢\nОтправь фото или картинку (JPEG, PNG, WebP)"
        if status_msg:
            await status_msg.edit_text(err_text)
        else:
            await message.answer(err_text)
        if user.id not in ADMIN_USER_IDS:
            await _refund_token(user.id, reason)

    except Exception as e:
        logger.error(f"Photo processing failed for user {user.id}: {e}", exc_info=True)
        err_text = "Извините, заняло чуть дольше, чем обычно"
        if status_msg:
            await status_msg.edit_text(err_text)
        else:
            await message.answer(err_text)
        if user.id not in ADMIN_USER_IDS:
            await _refund_token(user.id, reason)


async def _refund_token(user_id: int, reason: str):
    try:
        if reason == "paid":
            await database.add_paid_tokens(user_id, 1)
        elif reason == "free":
            await database.unuse_free_token(user_id)
    except Exception as e:
        logger.warning(f"Token refund failed for user {user_id}: {e}")


async def _send_milestone_congrats(message: Message, total: int):
    if total == 5:
        try:
            await message.answer_photo(
                photo=FSInputFile(CONGRATS_5_GEN_IMAGE),
                caption="Уиииии! ❤️❤️❤️ \nМы с тобой вырезали целых 5 картинок!\nКакие мы молодцы. Так держать! 💪",
            )
        except Exception as e:
            logger.warning(f"Could not send 5-gen congrats: {e}")

    elif total == 10:
        try:
            await message.answer_photo(
                photo=FSInputFile(CONGRATS_10_GEN_IMAGE),
                caption="Только представь...\n\nмы...с тобой...вырезали...10 картинок! 🎂\nПоздравляю, ты стал настоящим другом Кэти. Кэти тебя никогда не забудет!",
            )
        except Exception as e:
            logger.warning(f"Could not send 10-gen congrats: {e}")


@router.message(F.photo)
async def on_photo(message: Message, bot: Bot):
    await process_photo(message, bot)


@router.message(F.document)
async def on_document(message: Message, bot: Bot):
    doc = message.document
    if doc and doc.mime_type and doc.mime_type.startswith("image/"):
        await process_photo(message, bot)
    else:
        await message.answer(
            "Это не картинка 🤔 Отправь фото или файл-изображение (JPEG, PNG, WebP) ✂️"
        )
