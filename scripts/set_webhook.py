import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")

if not BOT_TOKEN:
    print("BOT_TOKEN topilmadi")
    sys.exit(1)

if not WEBAPP_URL:
    print("WEBAPP_URL topilmadi")
    sys.exit(1)

webhook_url = f"{WEBAPP_URL}/api/bot"
api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"

response = requests.get(api_url, params={"url": webhook_url}, timeout=20)

print(response.status_code)
print(response.text)
