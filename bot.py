import os
import time
import hmac
import hashlib
import requests


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

ALIEXPRESS_APP_KEY = os.environ["ALIEXPRESS_APP_KEY"]
ALIEXPRESS_APP_SECRET = os.environ["ALIEXPRESS_APP_SECRET"]
ALIEXPRESS_TRACKING_ID = os.environ["ALIEXPRESS_TRACKING_ID"]

ALIEXPRESS_URL = "https://api-sg.aliexpress.com/sync"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# =========================
# ALIEXPRESS SIGNATURE
# =========================

def sign_aliexpress_request(params):
    params_to_sign = {
        key: str(value)
        for key, value in params.items()
        if key != "sign" and value is not None
    }

    sorted_params = sorted(params_to_sign.items())

    sign_string = "".join(
        key + value
        for key, value in sorted_params
    )

    return hmac.new(
        ALIEXPRESS_APP_SECRET.encode("utf-8"),
        sign_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()


# =========================
# CALL ALIEXPRESS
# =========================

def call_aliexpress(method, business_params):
    params = {
        "app_key": ALIEXPRESS_APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "method": method,
    }

    params.update(business_params)
    params["sign"] = sign_aliexpress_request(params)

    response = requests.get(
        ALIEXPRESS_URL,
        params=params,
        timeout=30,
    )

    print("AliExpress status:", response.status_code)
    print("AliExpress response:", response.text)

    response.raise_for_status()
    return response.json()


# =========================
# FIND PRODUCT
# =========================

def find_product():
    data = call_aliexpress(
        "aliexpress.affiliate.product.query",
        {
            "keywords": "dog",
            "page_no": "1",
            "page_size": "5",
            "ship_to_country": "IL",
            "target_currency": "ILS",
            "target_language": "EN",
        },
    )

    response_data = data.get(
        "aliexpress_affiliate_product_query_response", {}
    )

    result = response_data.get("resp_result", {}).get("result", {})
    products = result.get("products", {}).get("product", [])

    if not products:
        raise RuntimeError("No AliExpress products found.")

    return products[0]


# =========================
# GENERATE AFFILIATE LINK
# =========================

def generate_affiliate_link(product_url):
    data = call_aliexpress(
        "aliexpress.affiliate.link.generate",
        {
            "source_values": product_url,
            "tracking_id": ALIEXPRESS_TRACKING_ID,
            "promotion_link_type": "0",
        },
    )

    response_data = data.get(
        "aliexpress_affiliate_link_generate_response", {}
    )

    result = response_data.get("resp_result", {}).get("result", {})
    links = result.get("promotion_links", {}).get("promotion_link", [])

    if not links:
        raise RuntimeError("No affiliate link returned.")

    return links[0]["promotion_link"]


# =========================
# TELEGRAM
# =========================

def send_product_to_telegram(product, affiliate_link):
    title = product.get("product_title", "AliExpress Deal")

    price = (
        product.get("target_sale_price")
        or product.get("sale_price")
        or "See current price"
    )

    image_url = product.get("product_main_image_url", "")

    message = (
        f"🐶 {title}\n\n"
        f"💰 מחיר: {price}\n\n"
        f"🛒 להזמנה:\n{affiliate_link}"
    )

    if image_url:
        response = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            data={
                "chat_id": CHANNEL_ID,
                "photo": image_url,
                "caption": message[:1024],
            },
            timeout=30,
        )
    else:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            data={
                "chat_id": CHANNEL_ID,
                "text": message,
            },
            timeout=30,
        )

    print("Telegram status:", response.status_code)
    print("Telegram response:", response.text)

    response.raise_for_status()


# =========================
# MAIN
# =========================

def main():
    print("Metziot Express bot started successfully.")

    product = find_product()

    print("Product found:")
    print(product.get("product_title"))

    product_url = product.get("product_detail_url")

    if not product_url:
        raise RuntimeError("Product has no product_detail_url.")

    affiliate_link = generate_affiliate_link(product_url)

    print("Affiliate link generated successfully.")

    send_product_to_telegram(product, affiliate_link)

    print("Product posted successfully to Telegram.")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
