"""
Runs on GitHub's servers (not your computer).
Opens the Pokémon Center page in a real browser and sends a push
notification to your phone via ntfy when the item looks in stock.
"""
import os
import requests
from playwright.sync_api import sync_playwright

PRODUCT_URL = "https://www.pokemoncenter.com/en-ca/product/10-10451-115/pokemon-tcg-30th-celebration-booster-bundle-6-packs"
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
MANUAL_RUN = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

OUT_OF_STOCK = ["out of stock", "sold out", "currently unavailable"]
BLOCK_SIGNS = ["access denied", "incapsula", "request unsuccessful", "verify you are human", "pardon our interruption"]


def notify(title, message, priority="urgent"):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": title, "Priority": priority, "Click": PRODUCT_URL, "Tags": "rotating_light"},
        timeout=15,
    )


def get_status():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/129.0 Safari/537.36",
            locale="en-CA",
        )
        page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)
        text = page.inner_text("body").lower()

        if any(s in text for s in BLOCK_SIGNS):
            return "BLOCKED"
        if "waiting room" in text or "you are now in line" in text:
            return "QUEUE"
        if any(s in text for s in OUT_OF_STOCK):
            return "OUT"
        for btn in page.get_by_role("button").all():
            try:
                if "add to cart" in btn.inner_text().lower() and btn.is_enabled():
                    return "IN"
            except Exception:
                pass
        return "UNKNOWN"


status = get_status()
print("Status:", status)

if status == "IN":
    notify("IN STOCK!", "30th Celebration Booster Bundle looks available. Tap to open.")
elif status == "QUEUE":
    notify("Queue is up!", "Pokémon Center waiting room is active. Tap to join.")
elif MANUAL_RUN:
    # Test runs always report back so you know the setup works
    notify(f"Test run: {status}", f"Watcher is working. Current status: {status}", priority="default")
