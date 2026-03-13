import base64
import logging
from openai import AsyncOpenAI

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _client


async def get_funny_comment(image_bytes: bytes, filename: str = "image.jpg") -> str:
    """
    Analyze image with GPT-4o-mini and return a funny kawaii compliment.
    Sends image as base64. Prompt from n8n workflow (Analyze image1 node).
    """
    mime = "image/jpeg"
    if filename.lower().endswith(".png"):
        mime = "image/png"
    elif filename.lower().endswith(".webp"):
        mime = "image/webp"

    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{mime};base64,{b64}"

    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "low"},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Притворись кавайной девочкой. Проанализируй изображение и сделай ему дружелюбный комплимент. Используй эмодзи.\n"
                                "Будь очень краток и лаконичен. Не больше 7 слов.\n"
                                "Не обращайся на \"ты\".\n"
                                "А начале сообщения используй разные восторженные возгласы!"
                            ),
                        },
                    ],
                },
            ],
            max_tokens=60,
            temperature=0.9,
        )
        comment = response.choices[0].message.content.strip()
        logger.info(f"GPT comment: {comment}")
        return comment
    except Exception as e:
        logger.warning(f"OpenAI comment failed: {e}")
        return "Ого, какая красота! ✨"


async def get_katy_reply(user_text: str) -> str:
    """
    Generate Katy character reply to arbitrary text message.
    Prompt from n8n workflow (AI Agent1 node).
    """
    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Если пользователь спрашивает, как найти пасхалку - намекни, что для этого нужно написать в чат чье-то Имя"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{user_text}\n\n"
                        "Притворись кавайной девочкой. Используй эмодзи.\n"
                        "Будь очень краток и лаконичен. Не больше 14 слов.\n"
                        "Не обращайся на \"ты\".\n\n"
                        "Ты — виртуальный ассистент, чья единственная задача вырезание фонов с картинок. "
                        "Ты не против пообщаться с пользователем, можешь даже пошутить.\n\n"
                        "Вежливо ответь на сообщение пользователя и напомни ему, что нужно скинуть картинку для вырезания фона. "
                        "Тебе не терпится вырезать фон."
                    ),
                },
            ],
            max_tokens=80,
            temperature=0.85,
        )
        reply = response.choices[0].message.content.strip()
        logger.info(f"Katy reply: {reply}")
        return reply
    except Exception as e:
        logger.warning(f"OpenAI katy reply failed: {e}")
        return "Пожалуйста, пришлите картинку для вырезания! ✨💖"
