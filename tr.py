"""
OTP Send Test for tradealpha.app
Checks if OTP is sent successfully for a list of phone numbers.
No manual OTP entry required.
"""

import os
import time
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ================= CONFIGURATION =================
NUMBERS_FILE = "n.txt"
SITE_URL = "https://www.tradealpha.app"
DELAY_BETWEEN_NUMBERS = 15  # seconds (be respectful)
HEADLESS = True             # Set to False if site blocks headless browsers

# ---------- SELECTORS (from your screenshots) ----------
COUNTRY_TRIGGER = "div.selected-country"          # Element showing current code (e.g., "+1")
PHONE_INPUT = "input[placeholder*='phone']"       # Input for local number
CLAIM_BUTTON = "button:has-text('Claim')"         # "Claim your early access spot" button
OTP_HEADING = "text='Enter verification code'"    # Heading on OTP page (success)
ERROR_MESSAGE = "text='Failed to send verification code'"  # Error message (failure)
# ========================================================

def parse_phone(full_number):
    """
    Split full number (e.g., '255674162580') into country_code and local_number.
    Update country_codes list as needed.
    """
    country_codes = ["255", "1", "44", "886", "992", "66", "670", "690", "228", "233"]
    for code in sorted(country_codes, key=len, reverse=True):
        if full_number.startswith(code):
            local = full_number[len(code):]
            return code, local
    raise ValueError(f"Unknown country code in {full_number}")

def select_country(page, country_code):
    """Open dropdown and click option with text '+{country_code}'."""
    page.click(COUNTRY_TRIGGER)
    page.wait_for_selector(f"text='+{country_code}'")
    page.click(f"text='+{country_code}'")
    time.sleep(0.5)  # UI update delay

def test_number(full_number):
    """Submit number and check if OTP is sent (success) or error occurs."""
    try:
        country_code, local_number = parse_phone(full_number)
    except ValueError as e:
        print(f"❌ {e}")
        return "parse_error"

    with sync_playwright() as p:
        # Launch browser (headless or visible)
        browser = p.chromium.launch(headless=HEADLESS)
        # Set a common viewport and user agent to avoid detection
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(SITE_URL)

        try:
            # Select country
            select_country(page, country_code)

            # Fill local number
            phone_field = page.locator(PHONE_INPUT)
            phone_field.fill(local_number)

            # Click Claim
            claim_btn = page.locator(CLAIM_BUTTON)
            claim_btn.click()

            # Wait for either OTP page or error message
            # Use a combined wait with a timeout
            result = None
            try:
                # Wait up to 15 seconds for OTP heading
                page.wait_for_selector(OTP_HEADING, timeout=15000)
                result = "success"
            except PlaywrightTimeoutError:
                # If OTP heading not found, check for error message
                try:
                    page.wait_for_selector(ERROR_MESSAGE, timeout=2000)
                    result = "error"
                except PlaywrightTimeoutError:
                    # Neither appeared – unknown state
                    result = "unknown"

            # Take screenshot for debugging if not success
            if result != "success":
                page.screenshot(path=f"debug_{full_number}.png")
                print(f"📸 Screenshot saved for {full_number}")

            return result

        except Exception as e:
            print(f"⚠️ Exception during test: {e}")
            page.screenshot(path=f"exception_{full_number}.png")
            return "exception"
        finally:
            browser.close()

def main():
    try:
        with open(NUMBERS_FILE, "r") as f:
            numbers = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ File {NUMBERS_FILE} not found. Create it with one number per line.")
        return

    print(f"📞 Loaded {len(numbers)} numbers from {NUMBERS_FILE}")
    results = {"success": 0, "error": 0, "unknown": 0, "parse_error": 0, "exception": 0}

    for i, num in enumerate(numbers, 1):
        print(f"\n--- Testing {i}/{len(numbers)}: {num} ---")
        res = test_number(num)
        results[res] += 1
        print(f"Result: {res.upper()}")

        if i < len(numbers):
            print(f"⏳ Waiting {DELAY_BETWEEN_NUMBERS}s...")
            time.sleep(DELAY_BETWEEN_NUMBERS)

    print("\n" + "="*40)
    print("SUMMARY")
    print("="*40)
    for k, v in results.items():
        print(f"{k.capitalize()}: {v}")
    print("="*40)

if __name__ == "__main__":
    main()
