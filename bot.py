import os
import time
import hmac
import hashlib
import requests


# ==================================================
# SETTINGS
# ==================================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

ALIEXPRESS_APP_KEY = os.environ["ALIEXPRESS_APP_KEY"]
ALIEXPRESS_APP_SECRET = os.environ["ALIEXPRESS_APP_SECRET"]
ALIEXPRESS_TRACKING_ID = os.environ["ALIEXPRESS_TRACKING_ID"]

ALIEXPRESS_URL = "https://api-sg.aliexpress.com/sync"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

POST_INTERVAL = 3 * 60 * 60


# ==================================================
# VERY SPECIFIC DOG SEARCHES
# ==================================================

DOG_SEARCHES = [
    "dog leash pet",
    "dog harness pet",
    "dog collar pet",
    "dog chew toy pet",
    "dog rope toy pet",
    "dog ball toy pet",
    "dog interactive toy pet",
    "dog slow feeder bowl",
    "dog food bowl pet",
    "dog water bottle pet",
    "dog grooming brush pet",
    "dog nail clipper pet",
    "dog poop bag dispenser",
    "dog car seat belt pet",
    "dog car seat cover pet",
    "dog bed pet",
    "dog training toy pet",
]


# ==================================================
# PRODUCT MUST HAVE ONE WORD FROM EACH GROUP
# ==================================================

# The title must clearly indicate a dog/pet product.

ANIMAL_WORDS = [
    "dog",
    "dogs",
    "puppy",
    "puppies",
    "canine",
    "pet",
]


# And it must contain an actual pet-product/use word.

USE_WORDS = [
    "leash",
    "lead",
    "harness",
    "collar",

    "toy",
    "chew",
    "rope",
    "ball",
    "frisbee",

    "bowl",
    "feeder",
    "feeding",

    "water bottle",
    "drinker",

    "brush",
    "grooming",
    "comb",
    "nail clipper",

    "poop bag",
    "waste bag",
    "bag dispenser",

    "seat belt",
    "car seat",
    "car cover",
    "seat cover",

    "bed",
    "mat",
    "kennel",

    "training",
    "treat",
    "snuffle",
]


# ==================================================
# NEVER ALLOW THESE PRODUCTS
# ==================================================

BLOCKED_WORDS = [
    "sticker",
    "stickers",
    "decal",
    "poster",
    "painting",
    "canvas",
    "wall art",
    "wall decor",

    "t-shirt",
    "t shirt",
    "shirt",
    "hoodie",
    "sweatshirt",
    "sweater",

    "sock",
    "socks",
    "slipper",
    "slippers",
    "shoe",
    "shoes",

    "phone case",
    "iphone case",

    "keychain",
    "key chain",

    "necklace",
    "earring",
    "earrings",
    "bracelet",
    "jewelry",

    "figurine",
    "ornament",
    "decoration",

    "plush",
    "doll",
    "stuffed animal",

    "costume",
    "cosplay",

    "backpack",
    "handbag",
    "wallet",

    "mug",
    "cup",

    "pillow cover",
    "cushion cover",

    "print",
    "printed",
]


# ==================================================
# SIGN ALIEXPRESS REQUEST
# ==================================================

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


# ==================================================
# CALL ALIEXPRESS
# ==================================================

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


# ==================================================
# NUMBER HELPER
# ==================================================

def number(value, default=0):

    try:

        if value is None:
            return default

        return float(
            str(value)
            .replace("%", "")
            .replace(",", "")
            .strip()
        )

    except (TypeError, ValueError):

        return default


# ==================================================
# PRODUCT DATA
# ==================================================

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

    discount = number(
        product.get("discount")
    )

    if discount > 0:
        return discount

    original = get_original_price(product)
    sale = get_sale_price(product)

    if original > 0 and sale > 0 and sale < original:

        return round(
            ((original - sale) / original) * 100
        )

    return 0


# ==================================================
# STRICT DOG PRODUCT CHECK
# ==================================================

def is_definitely_dog_product(product):

    title = str(
        product.get("product_title", "")
    ).lower().strip()

    if not title:
        return False


    # ----------------------------------------------
    # STEP 1: BLOCK UNRELATED MERCHANDISE
    # ----------------------------------------------

    for word in BLOCKED_WORDS:

        if word in title:

            print(
                "REJECTED BLOCKED:",
                title[:150]
            )

            return False


    # ----------------------------------------------
    # STEP 2: MUST MENTION DOG/PET
    # ----------------------------------------------

    has_animal_word = any(
        word in title
        for word in ANIMAL_WORDS
    )

    if not has_animal_word:

        print(
            "REJECTED - NO DOG/PET:",
            title[:150]
        )

        return False


    # ----------------------------------------------
    # STEP 3: MUST BE AN ACTUAL PET PRODUCT
    # ----------------------------------------------

    has_use_word = any(
        word in title
        for word in USE_WORDS
    )

    if not has_use_word:

        print(
            "REJECTED - NOT DOG EQUIPMENT:",
            title[:150]
        )

        return False


    print(
        "VALID DOG PRODUCT:",
        title[:150]
    )

    return True


# ==================================================
# DEAL CHECK
# ==================================================

def is_good_deal(product):

    if not is_definitely_dog_product(product):
        return False

    sale_price = get_sale_price(product)

    discount = get_discount(product)

    if sale_price <= 0:
        return False

    # We only want a meaningful discount.
    if discount < 20:
        return False

    return True


# ==================================================
# SCORE
# ==================================================

def product_score(product):

    discount = get_discount(product)
    orders = get_orders(product)
    commission = get_commission(product)

    score = 0


    # Discount is most important.

    score += min(discount, 70) * 5


    # Popularity helps us avoid junk.

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


    # Strong discount bonus.

    if discount >= 50:
        score += 100

    elif discount >= 40:
        score += 75

    elif discount >= 30:
        score += 50

    elif discount >= 20:
        score += 25


    # Commission is secondary.

    score += min(commission, 20) * 2


    return score


# ==================================================
# SEARCH
# ==================================================

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
            # Search/filter in English.
            # This makes our strict filtering reliable.
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


# ==================================================
# FIND BEST PRODUCT
# ==================================================

def find_best_deal():

    all_products = []


    for keyword in DOG_SEARCHES:

        try:

            print("SEARCHING:", keyword)

            products = search_products(keyword)

            all_products.extend(products)

        except Exception as error:

            print(
                "SEARCH ERROR:",
                keyword,
                error
            )


    if not all_products:

        raise RuntimeError(
            "No products returned by AliExpress."
        )


    # ----------------------------------------------
    # REMOVE DUPLICATES
    # ----------------------------------------------

    unique_products = {}


    for product in all_products:

        product_id = str(
            product.get("product_id", "")
        )

        if product_id:

            unique_products[product_id] = product


    print(
        "TOTAL UNIQUE PRODUCTS:",
        len(unique_products)
    )


    # ----------------------------------------------
    # STRICT FILTER
    # ----------------------------------------------

    good_products = []


    for product in unique_products.values():

        if is_good_deal(product):

            good_products.append(product)


    print(
        "REAL DOG DEALS FOUND:",
        len(good_products)
    )


    if not good_products:

        raise RuntimeError(
            "No genuine dog deals passed the strict filter."
        )


    # ----------------------------------------------
    # SORT
    # ----------------------------------------------

    good_products.sort(
        key=product_score,
        reverse=True,
    )


    best = good_products[0]


    print(
        "SELECTED DOG PRODUCT:",
        best.get("product_title")
    )

    print(
        "DISCOUNT:",
        get_discount(best)
    )

    print(
        "ORDERS USED INTERNALLY:",
        get_orders(best)
    )

    print(
        "SCORE:",
        product_score(best)
    )


    return best


# ==================================================
# AFFILIATE LINK
# ==================================================

def generate_affiliate_link(product_url):

    data = call_aliexpress(

        "aliexpress.affiliate.link.generate",

        {
            "source_values": product_url,

            "tracking_id":
                ALIEXPRESS_TRACKING_ID,

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


# ==================================================
# SIMPLE HEBREW TITLE
# ==================================================

def create_hebrew_title(product):

    english_title = str(
        product.get("product_title", "")
    ).lower()


    if "harness" in english_title:
        return "רתמה לכלב"

    if "leash" in english_title or " lead " in f" {english_title} ":
        return "רצועה לכלב"

    if "collar" in english_title:
        return "קולר לכלב"

    if "slow feeder" in english_title:
        return "קערת האכלה איטית לכלב"

    if "bowl" in english_title or "feeder" in english_title:
        return "קערת אוכל לכלב"

    if "water bottle" in english_title or "drinker" in english_title:
        return "בקבוק מים נייד לכלב"

    if "grooming" in english_title or "brush" in english_title:
        return "אביזר טיפוח לכלב"

    if "nail clipper" in english_title:
        return "קוצץ ציפורניים לכלב"

    if "poop bag" in english_title or "waste bag" in english_title:
        return "מתקן לשקיות איסוף לכלב"

    if "seat belt" in english_title:
        return "חגורת בטיחות לכלב לרכב"

    if "seat cover" in english_title or "car cover" in english_title:
        return "כיסוי מושב לרכב לכלב"

    if "bed" in english_title:
        return "מיטה נוחה לכלב"

    if "toy" in english_title or "ball" in english_title:
        return "צעצוע לכלב"

    if "training" in english_title:
        return "אביזר אילוף לכלב"


    return "אביזר שימושי לכלב"


# ==================================================
# TELEGRAM
# ==================================================

def send_product_to_telegram(
    product,
    affiliate_link
):

    title = create_hebrew_title(product)

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
        ""
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
        f"💰 עכשיו רק: {sale_price} ₪\n\n"
        "🛒 לרכישה ב-AliExpress:\n"
        f"{affiliate_link}\n\n"
        "⏰ המחיר והמבצע עשויים להשתנות."
    )


    # NO SALES COUNT IN THE TELEGRAM POST.

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
        response.status_code
    )

    print(
        "Telegram response:",
        response.text
    )

    response.raise_for_status()


# ==================================================
# POST
# ==================================================

def post_deal():

    print(
        "Searching ONLY for genuine dog products..."
    )

    product = find_best_deal()

    product_url = product.get(
        "product_detail_url"
    )

    if not product_url:

        raise RuntimeError(
            "Product has no product_detail_url."
        )


    affiliate_link = generate_affiliate_link(
        product_url
    )


    send_product_to_telegram(
        product,
        affiliate_link
    )


    print(
        "Genuine dog deal posted successfully."
    )


# ==================================================
# MAIN
# ==================================================

def main():

    print(
        "Dog Deals bot started."
    )


    while True:

        try:

            post_deal()

        except Exception as error:

            print(
                "ERROR:",
                error
            )


        print(
            "Waiting 3 hours..."
        )


        time.sleep(
            POST_INTERVAL
        )


if __name__ == "__main__":
    main()
