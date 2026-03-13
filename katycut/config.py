import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FAL_API_KEY = os.getenv("FAL_API_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
UPLOADTHING_SECRET = os.getenv("UPLOADTHING_SECRET")
UPLOADTHING_APP_ID = os.getenv("UPLOADTHING_APP_ID", "wdxq1pmuw9")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID", "0"))
NOTIFY_BOT_TOKEN = os.getenv("NOTIFY_BOT_TOKEN")
ADMIN_USER_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_USER_IDS", "").split(",")
    if x.strip().isdigit()
]

# Payment packages
PAYMENT_PACKAGES = [
    {"tokens": 5, "price": 69, "label": "5 вырезок — 69 ₽"},
    {"tokens": 15, "price": 149, "label": "15 вырезок — 149 ₽"},
    {"tokens": 50, "price": 399, "label": "50 вырезок — 399 ₽"},
    {"tokens": 200, "price": 999, "label": "200 вырезок — 999 ₽"},
]

# Local image paths (files in src/ folder)
CONGRATS_5_GEN_IMAGE = "src/Katy05.jpg"
CONGRATS_10_GEN_IMAGE = "src/Katy10.jpg"
EASTER_EGG_GATS_IMAGE = "src/KatyGats.jpg"

# Keep URL versions for congrats (sent as URL or local file - both supported)
CONGRATS_5_GEN_URL = os.getenv("CONGRATS_5_GEN_URL", "")
CONGRATS_10_GEN_URL = os.getenv("CONGRATS_10_GEN_URL", "")

# FAL.ai endpoints
FAL_QUEUE_URL = "https://queue.fal.run/fal-ai/bria/background/remove"
FAL_RESULT_URL = "https://queue.fal.run/fal-ai/bria/requests/{request_id}"

# UploadThing API
UPLOADTHING_API_URL = "https://api.uploadthing.com/v7"
