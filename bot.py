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

# Publish every 3 hours
POST_INTERVAL = 3 * 60 * 60

# Dog-product searches
DOG_SEARCHES = [
    "dog toys",
    "dog accessories",
    "dog leash",
    "dog collar",
    "dog bed",
    "dog grooming",
    "dog bowl",
    "dog car accessories",
]


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
# ALIEXPRESS REQUEST
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
    print("AliExpress response:", response.text[:1000])

    response.raise_for_status()

    data = response.json()

    if "error_response" in data:
        raise RuntimeError(
            f"AliExpress error: {data['error_response']}"
        )

    return data


# =========================
# PRODUCT HELPERS
# =========================

def number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_discount(product):
    discount = number(product.get("discount"))

    if discount > 0:
        return discount

    original = number(
        product.get("target_original_price")
        or product.get("original_price")
    )

    sale = number(
        product.get("target_sale_price")
        or product.get("sale_price")
    )

    if original > 0 and sale > 0 and sale < original:
        return round(
            (original - sale) / original * 100
        )

    return 0


def product_score(product):
    discount = get_discount(product)

    orders = number(
        product.get("lastest_volume")
        or product.get("volume")
    )

    commission = number(
        product.get("commission_rate")
    )

    # Biggest priority = real discount.
    # Sales/popularity and commission are secondary.
    return (
        discount * 10
        + min(orders, 10000) / 100
        + commission
    )


# =========================
# FIND DOG DEALS
# =========================

def search_products(keyword):
    data = call_aliexpress(
        "aliexpress.affiliate.product.query",
        {
            "keywords": keyword,
            "page_no": "1",
            "page_size": "20",
            "ship_to_country": "IL",
            "target_currency": "ILS",

            # Ask AliExpress for Hebrew
            "target_language": "HE",
        },
    )

    response_data = data.get(
        "aliexpress_affiliate_product_query_response",
        {},
    )

    result = response_data.get(
        "resp_result",
        {},
    ).get(
        "result",
        {},
    )

    return result.get(
        "products",
        {},
    ).get(
        "product",
        [],
    )


def find_best_deal():
    all_products = []

    for keyword in DOG_SEARCHES:
        try:
            products = search_products(keyword)
            all_products.extend(products)

        except Exception as error:
            print(
                f"Search failed for {keyword}: {error}"
            )

    if not all_products:
        raise RuntimeError(
            "No dog products found."
        )

    # Remove duplicates
    unique_products = {}

    for product in all_products:
        product_id = str(
            product.get("product_id", "")
        )

        if product_id:
            unique_products[product_id] = product

    products = list(
        unique_products.values()
    )

    if not products:
        raise RuntimeError(
            "No unique products found."
        )

    products.sort(
        key=product_score,
        reverse=True,
    )

    return products[0]


# =========================
# AFFILIATE LINK
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
        "aliexpress_affiliate_link_generate_response",
        {},
    )

    result = response_data.get(
        "resp_result",
        {},
    ).get(
        "result",
        {},
    )

    links = result.get(
        "promotion_links",
        {},
    ).get(
        "promotion_link",
        [],
    )

    if not links:
        raise RuntimeError(
            "No affiliate link returned."
        )

    return links[0]["promotion_link"]


# =========================
# TELEGRAM
# =========================

def send_product_to_telegram(
    product,
    affiliate_link,
):
    title = product.get(
        "product_title",
        "מוצר שווה לכלבים 🐶",
    )

    sale_price = (
        product.get("target_sale_price")
        or product.get("sale_price")
        or "בדקו בקישור"
    )

    original_price = (
        product.get("target_original_price")
        or product.get("original_price")
    )

    discount = get_discount(product)

    image_url = product.get(
        "product_main_image_url",
        "",
    )

    # Build a fully Hebrew-style post
    message = (
        "🐶🔥 מציאה שווה לכלב שלכם!\n\n"
        f"⭐ {title}\n\n"
    )

    if discount > 0:
        message += (
            f"🏷️ הנחה של כ-{discount:.0f}%\n"
        )

    if original_price:
        message += (
            f"❌ במקום: {original_price} ₪\n"
        )

    message += (
        f"💰 עכשיו רק: {sale_price} ₪\n\n"
        "🛒 לרכישה ב-AliExpress:\n"
        f"{affiliate_link}\n\n"
        "⏰ המחיר והמבצע עשויים להשתנות."
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

    print(
        "Telegram status:",
        response.status_code,
    )

    print(
        "Telegram response:",
        response.text,
    )

    response.raise_for_status()


# =========================
# POST ONE DEAL
# =========================

def post_deal():
    print(
        "Searching for the best dog deal..."
    )

    product = find_best_deal()

    print(
        "Selected product:",
        product.get("product_title"),
    )

    print(
        "Discount:",
        get_discount(product),
    )

    product_url = product.get(
        "product_detail_url"
    )

    if not product_url:
        raise RuntimeError(
            "Product has no product_detail_url."
        )

    affiliate_link = (
        generate_affiliate_link(
            product_url
        )
    )

    send_product_to_telegram(
        product,
        affiliate_link,
    )

    print(
        "Deal posted successfully."
    )


# =========================
# MAIN
# =========================

def main():
    print(
        "Metziot Express bot started."
    )

    while True:
        try:
            post_deal()

        except Exception as error:
            print(
                "ERROR:",
                error,
            )

        print(
            "Waiting 3 hours..."
        )

        time.sleep(
            POST_INTERVAL
        )


if __name__ == "__main__":
    main()
