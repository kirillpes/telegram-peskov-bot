import asyncio
import logging
import uuid

from aiogram import Router, F, Bot
from aiogram import Bot as AiogramBot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from yookassa import Configuration, Payment

import database
from config import (
    PAYMENT_PACKAGES,
    YOOKASSA_SHOP_ID,
    YOOKASSA_SECRET_KEY,
    ADMIN_TG_ID,
    NOTIFY_BOT_TOKEN,
)

logger = logging.getLogger(__name__)
router = Router()

BUY_TRIGGERS = {"купить", "buy", "/buy", "пополнить", "токены", "tokens"}

POLL_INTERVAL = 5   # seconds between checks
POLL_TIMEOUT = 600  # 10 minutes max


def _setup_yookassa():
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY


def _build_packages_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for i, pkg in enumerate(PAYMENT_PACKAGES):
        buttons.append([
            InlineKeyboardButton(
                text=pkg["label"],
                callback_data=f"buy_pkg:{i}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _poll_payment(bot: Bot, user_id: int, chat_id: int, payment_id: str, pkg: dict):
    """Poll YooKassa until payment succeeds or times out."""
    _setup_yookassa()
    elapsed = 0
    while elapsed < POLL_TIMEOUT:
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        try:
            payment = await asyncio.to_thread(Payment.find_one, payment_id)
            if payment.status == "succeeded":
                await database.add_paid_tokens(user_id, pkg["tokens"])
                await bot.send_message(
                    chat_id,
                    f"✅ Оплата прошла! Добавила {pkg['tokens']} вырезок на твой счёт ✂️✨\n"
                    f"Кидай фото — начинаем!",
                )
                try:
                    notify_bot = AiogramBot(token=NOTIFY_BOT_TOKEN)
                    await notify_bot.send_message(
                        ADMIN_TG_ID,
                        f"💰 Оплата! {pkg['label']} — user {user_id}",
                    )
                    await notify_bot.session.close()
                except Exception:
                    pass
                return
            elif payment.status in ("canceled",):
                await bot.send_message(chat_id, "Платёж отменён 😢")
                return
        except Exception as e:
            logger.warning(f"Poll error for payment {payment_id}: {e}")

    await bot.send_message(chat_id, "Время ожидания оплаты истекло. Напиши /buy чтобы попробовать снова.")


@router.message(F.text.func(lambda t: t and t.strip().lower() in BUY_TRIGGERS))
@router.message(Command("buy"))
async def handle_buy(message: Message):
    await database.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
    )
    await message.answer(
        "✂️ Выбери пакет вырезок:\n\n"
        "Каждый токен = 1 вырезка фона.\n"
        "Токены не сгорают! 💜",
        reply_markup=_build_packages_keyboard(),
    )


@router.callback_query(F.data.startswith("buy_pkg:"))
async def handle_buy_package(callback: CallbackQuery, bot: Bot):
    pkg_index = int(callback.data.split(":")[1])
    if pkg_index >= len(PAYMENT_PACKAGES):
        await callback.answer("Пакет не найден", show_alert=True)
        return

    pkg = PAYMENT_PACKAGES[pkg_index]
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    try:
        _setup_yookassa()
        bot_username = (await bot.get_me()).username
        payment = await asyncio.to_thread(
            Payment.create,
            {
                "amount": {"value": f"{pkg['price']}.00", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/{bot_username}",
                },
                "capture": True,
                "description": f"KatyCut: {pkg['label']} (user {user_id})",
                "metadata": {
                    "user_id": str(user_id),
                    "tokens": str(pkg["tokens"]),
                },
            },
            str(uuid.uuid4()),
        )

        payment_url = payment.confirmation.confirmation_url

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
        ])

        await callback.message.answer(
            f"💳 {pkg['label']}\n\nОплати по кнопке — токены придут автоматически ✨",
            reply_markup=keyboard,
        )
        await callback.answer()

        # Start background polling
        asyncio.create_task(_poll_payment(bot, user_id, chat_id, payment.id, pkg))

    except Exception as e:
        logger.error(f"YooKassa payment creation failed: {e}")
        await callback.answer("Ошибка при создании платежа 😢 Попробуй позже", show_alert=True)
