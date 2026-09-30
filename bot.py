import os
import time
import hmac
import hashlib
import requests
import random


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

APP_KEY = os.environ["ALIEXPRESS_APP_KEY"]
APP_SECRET = os.environ["ALIEXPRESS_APP_SECRET"]
TRACKING_ID = os.environ["ALIEXPRESS_TRACKING_ID"]

ALIEXPRESS_URL = "https://api-sg.aliexpress.com/sync"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

POST_EVERY = 3 * 60 * 60


# ============================================================
# PRODUCTS WE ACTUALLY WANT
#
# Each search has:
# search = what we ask AliExpress for
# required = phrase that MUST appear in the product title
# hebrew = what appears in Telegram
# ============================================================

PRODUCT_TYPES = [

    {
        "search": "interactive dog toy",
        "required": ["dog toy", "pet toy"],
        "hebrew": "צעצוע אינטראקטיבי לכלב 🧸",
    },

    {
        "search": "dog chew toy",
        "required": ["dog chew", "chew toy"],
        "hebrew": "צעצוע לעיסה לכלב 🦴",
    },

    {
        "search": "dog rope toy",
        "required": ["dog rope", "rope toy"],
        "hebrew": "צעצוע חבל לכלב 🪢",
    },

    {
        "search": "dog ball toy",
        "required": ["dog ball", "ball toy"],
        "hebrew": "כדור משחק לכלב 🎾",
    },

    {
        "search": "retractable dog leash",
        "required": ["dog leash", "retractable leash"],
        "hebrew": "רצועה נשלפת לכלב 🐕",
    },

    {
        "search": "dog walking leash",
        "required": ["dog leash", "walking leash"],
        "hebrew": "רצועת טיולים לכלב 🐕",
    },

    {
        "search": "dog harness vest",
        "required": ["dog harness", "pet harness"],
        "hebrew": "רתמה לכלב 🐕‍🦺",
    },

    {
        "search": "dog collar",
        "required": ["dog collar"],
        "hebrew": "קולר לכלב 🐶",
    },

    {
        "search": "dog winter jacket",
        "required": ["dog jacket", "dog coat"],
        "hebrew": "מעיל לכלב 🧥",
    },

    {
        "search": "dog sweater",
        "required": ["dog sweater"],
        "hebrew": "סוודר לכלב 🐶",
    },

    {
        "search": "dog raincoat",
        "required": ["dog raincoat"],
        "hebrew": "מעיל גשם לכלב 🌧️",
    },

    {
        "search": "dog shoes boots",
        "required": ["dog shoes", "dog boots"],
        "hebrew": "נעליים לכלב 🐾",
    },

    {
        "search": "dog deshedding brush",
        "required": [
            "dog deshedding",
            "deshedding brush",
            "de-shedding brush",
        ],
        "hebrew": "מברשת להסרת פרווה 🐕",
    },

    {
        "search": "dog grooming brush",
        "required": ["dog grooming brush"],
        "hebrew": "מברשת טיפוח לכלב 🪮",
    },

    {
        "search": "pet grooming vacuum dog",
        "required": [
            "grooming vacuum",
            "pet vacuum",
        ],
        "hebrew": "שואב פרווה וטיפוח לכלבים 🧹",
    },

    {
        "search": "dog bed washable",
        "required": ["dog bed"],
        "hebrew": "מיטה לכלב 🛏️",
    },

    {
        "search": "dog house kennel",
        "required": ["dog house", "dog kennel"],
        "hebrew": "בית לכלב 🏠",
    },

    {
        "search": "dog slow feeder bowl",
        "required": [
            "dog slow feeder",
            "slow feeder bowl",
        ],
        "hebrew": "קערת האכלה איטית לכלב 🥣",
    },

    {
        "search": "portable dog water bottle",
        "required": ["dog water bottle"],
        "hebrew": "בקבוק מים נייד לכלב 💧",
    },
]


# ============================================================
# HARD REJECTION
#
# We are not interested in components, replacement parts,
# decorative merchandise or tiny accessories.
# ============================================================

NEVER_ALLOW = [

    "adapter",
    "adaptor",

    "clip",
    "clips",

    "connector",
    "replacement",
    "spare part",

    "buckle",
    "hook only",

    "seat belt adapter",
    "seat belt clip",

    "metal clip",

    "sticker",
    "decal",

    "keychain",
    "key chain",

    "poster",
    "ornament",
    "figurine",

    "phone case",

    "necklace",
    "bracelet",
    "earring",

    "plush doll",
]


# ============================================================
# ALIEXPRESS SIGNING
# ============================================================

def sign(params):

    clean = {
        k: str(v)
        for k, v in params.items()
        if k != "sign" and v is not None
    }

    ordered = sorted(clean.items())

    raw = "".join(
        key + value
        for key, value in ordered
    )

    return hmac.new(
        APP_SECRET.encode(),
        raw.encode(),
        hashlib.sha256,
    ).hexdigest().upper()


# ============================================================
# ALIEXPRESS API
# ============================================================

def aliexpress(method, data):

    params = {
        "app_key": APP_KEY,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "method": method,
    }

    params.update(data)

    params["sign"] = sign(params)

    response = requests.get(
        ALIEXPRESS_URL,
        params=params,
        timeout=30,
    )

    print("AliExpress:", response.status_code)

    response.raise_for_status()

    result = response.json()

    if "error_response" in result:
        raise RuntimeError(result["error_response"])

    return result


# ============================================================
# NUMBER
# ============================================================

def num(value):

    try:

        return float(
            str(value)
            .replace("%", "")
            .replace(",", "")
        )

    except:

        return 0


# ============================================================
# PRODUCT VALUES
# ============================================================

def sale_price(product):

    return num(
        product.get("target_sale_price")
        or product.get("sale_price")
    )


def original_price(product):

    return num(
        product.get("target_original_price")
        or product.get("original_price")
    )


def orders(product):

    return num(
        product.get("lastest_volume")
        or product.get("volume")
    )


def discount(product):

    direct = num(
        product.get("discount")
    )

    if direct > 0:
        return direct

    old = original_price(product)
    new = sale_price(product)

    if old > new > 0:

        return round(
            ((old - new) / old) * 100
        )

    return 0


# ============================================================
# SEARCH ONE SPECIFIC PRODUCT TYPE
# ============================================================

def search_type(product_type):

    result = aliexpress(

        "aliexpress.affiliate.product.query",

        {
            "keywords": product_type["search"],
            "page_no": "1",
            "page_size": "30",
            "ship_to_country": "IL",
            "target_currency": "ILS",
            "target_language": "EN",
        },
    )

    root = result.get(
        "aliexpress_affiliate_product_query_response",
        {}
    )

    products = (
        root
        .get("resp_result", {})
        .get("result", {})
        .get("products", {})
        .get("product", [])
    )

    approved = []

    for product in products:

        title = str(
            product.get("product_title", "")
        ).lower()


        # ----------------------------------------
        # ABSOLUTE REJECTION
        # ----------------------------------------

        if any(
            bad in title
            for bad in NEVER_ALLOW
        ):

            continue


        # ----------------------------------------
        # MUST MATCH THIS EXACT PRODUCT TYPE
        # ----------------------------------------

        correct_product = any(
            phrase in title
            for phrase in product_type["required"]
        )

        if not correct_product:
            continue


        # ----------------------------------------
        # MUST ACTUALLY BE DOG/PET RELATED
        # ----------------------------------------

        if not any(
            animal in title
            for animal in [
                "dog",
                "puppy",
                "pet",
                "canine",
            ]
        ):

            continue


        # ----------------------------------------
        # BASIC QUALITY
        # ----------------------------------------

        if sale_price(product) <= 0:
            continue

        if discount(product) < 20:
            continue

        # We want products with proven demand.
        if orders(product) < 100:
            continue


        product["_hebrew_title"] = (
            product_type["hebrew"]
        )

        approved.append(product)


    return approved


# ============================================================
# SCORE
# ============================================================

def score(product):

    d = discount(product)
    sold = orders(product)

    points = d * 5


    if sold >= 10000:
        points += 300

    elif sold >= 5000:
        points += 250

    elif sold >= 2000:
        points += 200

    elif sold >= 1000:
        points += 160

    elif sold >= 500:
        points += 120

    elif sold >= 100:
        points += 70


    if d >= 50:
        points += 100

    elif d >= 40:
        points += 70

    elif d >= 30:
        points += 40


    return points


# ============================================================
# FIND DEAL
# ============================================================

def find_deal():

    candidates = []


    # Random order gives the channel variety instead
    # of always finding the same category first.

    searches = PRODUCT_TYPES.copy()

    random.shuffle(searches)


    for product_type in searches:

        print(
            "Searching:",
            product_type["search"]
        )

        try:

            found = search_type(
                product_type
            )

            candidates.extend(found)

        except Exception as e:

            print(
                "Search error:",
                e
            )


    if not candidates:

        raise RuntimeError(
            "No quality dog deals found."
        )


    # Remove duplicate product IDs.

    unique = {}

    for product in candidates:

        product_id = str(
            product.get("product_id", "")
        )

        if product_id:

            unique[product_id] = product


    candidates = list(
        unique.values()
    )


    candidates.sort(
        key=score,
        reverse=True
    )


    # Don't always select purely the #1 result.
    # Choose from the strongest five products,
    # giving the channel more variety.

    top = candidates[:5]

    chosen = random.choice(top)


    print(
        "FINAL PRODUCT:",
        chosen.get("product_title")
    )

    print(
        "CATEGORY:",
        chosen["_hebrew_title"]
    )

    print(
        "ORDERS:",
        orders(chosen)
    )

    print(
        "DISCOUNT:",
        discount(chosen)
    )


    return chosen


# ============================================================
# AFFILIATE LINK
# ============================================================

def affiliate_link(product):

    product_url = product.get(
        "product_detail_url"
    )

    if not product_url:

        raise RuntimeError(
            "Missing product URL"
        )


    result = aliexpress(

        "aliexpress.affiliate.link.generate",

        {
            "source_values": product_url,
            "tracking_id": TRACKING_ID,
            "promotion_link_type": "0",
        },
    )


    links = (
        result
        .get(
            "aliexpress_affiliate_link_generate_response",
            {}
        )
        .get("resp_result", {})
        .get("result", {})
        .get("promotion_links", {})
        .get("promotion_link", [])
    )


    if not links:

        raise RuntimeError(
            "Affiliate link was not generated."
        )


    return links[0]["promotion_link"]


# ============================================================
# TELEGRAM
# ============================================================

def send_to_telegram(product):

    link = affiliate_link(product)

    title = product["_hebrew_title"]

    new_price = (
        product.get("target_sale_price")
        or product.get("sale_price")
    )

    old_price = (
        product.get("target_original_price")
        or product.get("original_price")
    )

    d = discount(product)

    image = product.get(
        "product_main_image_url"
    )


    text = (
        "🐶🔥 מציאה שווה לכלב!\n\n"
        f"⭐ {title}\n\n"
    )


    if d:

        text += (
            f"🏷️ הנחה של כ-{d:.0f}%\n"
        )


    if old_price:

        text += (
            f"❌ במקום: {old_price} ₪\n"
        )


    text += (
        f"💰 מחיר מבצע: {new_price} ₪\n\n"
        "🛒 לרכישה ב-AliExpress:\n"
        f"{link}\n\n"
        "⏰ המחיר והמבצע עשויים להשתנות."
    )


    if image:

        response = requests.post(

            TELEGRAM_URL + "/sendPhoto",

            data={
                "chat_id": CHANNEL_ID,
                "photo": image,
                "caption": text,
            },

            timeout=30,
        )

    else:

        response = requests.post(

            TELEGRAM_URL + "/sendMessage",

            data={
                "chat_id": CHANNEL_ID,
                "text": text,
            },

            timeout=30,
        )


    print(
        "Telegram:",
        response.status_code
    )

    response.raise_for_status()


# ============================================================
# ONE RUN
# ============================================================

def run():

    print(
        "Looking for a quality dog deal..."
    )

    product = find_deal()

    send_to_telegram(product)

    print(
        "POST SUCCESSFUL"
    )


# ============================================================
# BOT
# ============================================================

def main():

    print(
        "NEW DOG DEALS BOT STARTED"
    )

    while True:

        try:

            run()

        except Exception as e:

            print(
                "ERROR:",
                e
            )


        print(
            "Next search in 3 hours."
        )

        time.sleep(
            POST_EVERY
        )


if __name__ == "__main__":
    main()
