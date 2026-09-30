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

POST_INTERVAL = 3 * 60 * 60


# =========================
# VERY SPECIFIC DOG SEARCHES
# =========================

DOG_SEARCHES = [
    "dog chew toy",
    "dog rope toy",
    "dog interactive toy",
    "dog squeaky toy",
    "dog leash walking",
    "dog harness walking",
    "dog collar adjustable",
    "dog grooming brush",
    "dog deshedding brush",
    "dog nail clipper",
    "dog food bowl",
    "dog slow feeder bowl",
    "dog portable water bottle",
    "dog poop bag dispenser",
    "dog car seat cover",
    "dog training treat pouch",
]


# =========================
# REQUIRED DOG-USE PHRASES
# =========================

DOG_USE_PHRASES = [
    "dog toy",
    "dog toys",
    "puppy toy",
    "puppy toys",
    "dog chew",
    "chew toy",
    "squeaky toy",
    "dog rope",
    "dog leash",
    "pet leash",
    "dog harness",
    "pet harness",
    "dog collar",
    "pet collar",
    "dog grooming",
    "pet grooming",
    "dog brush",
    "pet brush",
    "deshedding",
    "dog nail",
    "pet nail",
    "dog bowl",
    "pet bowl",
    "slow feeder",
    "dog water bottle",
    "pet water bottle",
    "dog poop bag",
    "pet poop bag",
    "dog seat cover",
    "pet seat cover",
    "dog car cover",
    "dog treat pouch",
    "dog training",
]


# Things that can mention dogs but are not products FOR dogs
BLOCKED_WORDS = [
    "sticker",
    "decal",
    "poster",
    "painting",
    "canvas",
    "wall art",
    "wall decor",
    "ornament",
    "figurine",
    "statue",
    "keychain",
    "key chain",
    "phone case",
    "iphone case",
    "necklace",
    "bracelet",
    "earring",
    "jewelry",
    "t-shirt",
    "tshirt",
    "shirt",
    "hoodie",
    "sweatshirt",
    "socks",
    "slippers",
    "pajama",
    "costume for women",
    "costume for men",
    "plush doll",
    "stuffed doll",
    "mug",
    "cup for human",
]


# =========================
# SIGNATURE
# =========================

def sign_aliexpress_request(params):
    params_to_sign = {
        key: str(value)
        for key, value in params.items()
        if key != "sign" and value is not None
    }

    sign_string = "".join(
        key + value
        for key, value in sorted(params_to_sign.items())
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

    response.raise_for_status()

    data = response.json()

    if "error_response" in data:
        raise RuntimeError(
            f"AliExpress error: {data['error_response']}"
        )

    return data


# =========================
# NUMBERS / PRICES
# =========================

def number(value, default=0):
    try:
        if value is None:
            return default

        return float(
            str(value).replace("%", "").strip()
        )

    except (TypeError, ValueError):
        return default


def get_sale_price(product):
    return number(
        product.get("target_sale_price")
        or product.get("sale_price")
    )


def get_original_price(product):
    return number(
        product.get("target_original_price")
        or product.get("original_price")
    )


def get_orders(product):
    return number(
        product.get("lastest_volume")
        or product.get("volume")
    )


def get_commission(product):
    return number(
        product.get("commission_rate")
    )


def get_discount(product):
    discount = number(product.get("discount"))

    if discount > 0:
        return discount

    original = get_original_price(product)
    sale = get_sale_price(product)

    if original > 0 and sale > 0 and sale < original:
        return round(
            (original - sale) / original * 100
        )

    return 0


# =========================
# STRICT DOG FILTER
# =========================

def is_real_dog_product(product):
    title = str(
        product.get("product_title", "")
    ).lower()

    if not title:
        return False

    # First reject obvious human/decorative merchandise
    for blocked in BLOCKED_WORDS:
        if blocked in title:
            print("BLOCKED:", title[:120])
            return False

    # Important:
    # "dog" by itself is NOT enough.
    # We require a phrase describing something actually used by a dog.
    for phrase in DOG_USE_PHRASES:
        if phrase in title:
            print("DOG PRODUCT:", title[:120])
            return True

    print("NOT DOG PRODUCT:", title[:120])
    return False


# =========================
# DEAL FILTER / SCORE
# =========================

def is_good_deal(product):
    if not is_real_dog_product(product):
        return False

    price = get_sale_price(product)
    discount = get_discount(product)
    orders = get_orders(product)

    if price <= 0:
        return False

    # Must show some evidence of being a worthwhile deal
    if discount < 15 and orders < 100:
        return False

    return True


def product_score(product):
    discount = get_discount(product)
    orders = get_orders(product)
    commission = get_commission(product)

    score = min(discount, 70) * 4

    if orders >= 10000:
        score += 180
    elif orders >= 5000:
        score += 150
    elif orders >= 1000:
        score += 120
    elif orders >= 500:
        score += 90
    elif orders >= 100:
        score += 60
    elif orders >= 20:
        score += 25

    if discount >= 50:
        score += 70
    elif discount >= 30:
        score += 50
    elif discount >= 20:
        score += 30

    score += min(commission, 20) * 2

    return score


# =========================
# SEARCH IN ENGLISH
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

            # IMPORTANT:
            # English is used for accurate filtering.
            "target_language": "EN",
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
    candidates = {}

    for keyword in DOG_SEARCHES:
        try:
            products = search_products(keyword)

            for product in products:
                product_id = str(
                    product.get("product_id", "")
                )

                if product_id and is_good_deal(product):
                    candidates[product_id] = product

        except Exception as error:
            print(
                f"Search failed for {keyword}: {error}"
            )

    if not candidates:
        raise RuntimeError(
            "No genuine dog deals found."
        )

    products = list(candidates.values())

    products.sort(
        key=product_score,
        reverse=True,
    )

    best = products[0]

    print("SELECTED:", best.get("product_title"))
    print("DISCOUNT:", get_discount(best))
    print("ORDERS:", get_orders(best))
    print("SCORE:", product_score(best))

    return best


# =========================
# HEBREW DISPLAY TITLE
# =========================

def hebrew_title(product):
    title = str(
        product.get("product_title", "")
    ).lower()

    if "harness" in title:
        return "רתמה נוחה לכלב 🐕"

    if "leash" in title:
        return "רצועה שימושית לטיולים עם הכלב 🐕‍🦺"

    if "collar" in title:
        return "קולר לכלב 🐶"

    if "slow feeder" in title:
        return "קערת האכלה איטית לכלב 🥣"

    if "bowl" in title:
        return "קערת אוכל או מים לכלב 🥣"

    if "water bottle" in title:
        return "בקבוק מים נייד לכלב 💧"

    if "grooming" in title or "brush" in title:
        return "אביזר טיפוח שימושי לכלב 🐶"

    if "nail" in title:
        return "קוצץ ציפורניים לכלבים 🐾"

    if "poop bag" in title:
        return "מתקן לשקיות איסוף לכלב 🐕"

    if "seat cover" in title or "car cover" in title:
        return "כיסוי לרכב לנסיעה עם הכלב 🚗🐶"

    if "treat pouch" in title:
        return "תיק חטיפים לאילוף הכלב 🦴"

    if "training" in title:
        return "אביזר אילוף לכלב 🐕"

    if (
        "toy" in title
        or "chew" in title
        or "squeaky" in title
        or "rope" in title
    ):
        return "צעצוע כיפי לכלב 🐶🦴"

    return "אביזר שימושי לכלב 🐶"


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

def send_product_to_telegram(product, affiliate_link):
    title = hebrew_title(product)

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
    orders = get_orders(product)

    image_url = product.get(
        "product_main_image_url",
        "",
    )

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
        f"💰 עכשיו רק: {sale_price} ₪\n"
    )

    if orders >= 100:
        message += (
            f"🔥 כבר נמכרו מעל {int(orders):,} יחידות\n"
        )

    message += (
        "\n🛒 לרכישה ב-AliExpress:\n"
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

    response.raise_for_status()


# =========================
# POST
# =========================

def post_deal():
    print(
        "Searching for genuine dog products..."
    )

    product = find_best_deal()

    product_url = product.get(
        "product_detail_url"
    )

    if not product_url:
        raise RuntimeError(
            "Product has no URL."
        )

    affiliate_link = generate_affiliate_link(
        product_url
    )

    send_product_to_telegram(
        product,
        affiliate_link,
    )

    print(
        "Genuine dog deal posted successfully."
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
