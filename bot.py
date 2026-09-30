import os
import requests
import time

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(text):
    response = requests.post(
        f"{API_URL}/sendMessage",
        data={
            "chat_id": CHANNEL_ID,
            "text": text,
            "disable_web_page_preview": False
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def main():
    print("Metziot Express bot started successfully.")
    send_message("TEST - Metziot Express bot is connected!")
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
