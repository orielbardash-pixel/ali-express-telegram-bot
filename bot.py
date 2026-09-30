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

ALIEXPRESS_URL = "https://api-sg.aliexpress.com/sync"
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


def sign_aliexpress_request(params):
    params_to_sign = {
        key: str(value)
        for key, value in params.items()
        if key != "sign" and value is not None
    }

    sorted_params = sorted(params_to_sign.items())

    sign_string = "".join(
        key + value for key, value in sorted_params
    )

    return hmac.new(
        ALIEXPRESS_APP_SECRET.encode("utf-8"),
        sign_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest().upper()

def test_aliexpress_api():
    params = {
        "app_key": ALIEXPRESS_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "method": "aliexpress.affiliate.product.query",
        "keywords": "dog",
        "page_no": "1",
        "page_size": "1",
        "ship_to_country": "IL",
        "target_currency": "ILS",
        "target_language": "EN"
    }

    params["sign"] = sign_aliexpress_request(params)

    response = requests.get(
        ALIEXPRESS_URL,
        params=params,
        timeout=30
    )

    print("AliExpress HTTP status:", response.status_code)
    print("AliExpress response:", response.text)

def main():
    print("Metziot Express bot started successfully.")
    print("Testing AliExpress API...")
    test_aliexpress_api()
    print("AliExpress API test finished.")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
