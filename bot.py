import os
import time
import hmac
import hashlib
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

ALIEXPRESS_APP_KEY = os.environ["ALIEXPRESS_APP_KEY"]
ALIEXPRESS_APP_SECRET = os.environ["ALIEXPRESS_APP_SECRET"]
ALIEXPRESS_TRACKING_ID = os.environ["ALIEXPRESS_TRACKING_ID"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(text):
    response = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        data={
            "chat_id": CHANNEL_ID,
            "text": text,
            "disable_web_page_preview": False
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def sign_aliexpress_request(api_name, params):
    params_to_sign = {
        key: str(value)
        for key, value in params.items()
        if key != "sign" and value is not None
    }

    sorted_params = sorted(params_to_sign.items())

    query = api_name + "".join(
        key + value for key, value in sorted_params
    )

    signature = hmac.new(
        ALIEXPRESS_APP_SECRET.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256
    ).hexdigest().upper()

    return signature


def main():
    print("Metziot Express bot started successfully.")
    print("Telegram configuration loaded.")
    print("AliExpress credentials loaded.")
    print("AliExpress tracking ID loaded.")
    print("Ready for AliExpress API test.")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
