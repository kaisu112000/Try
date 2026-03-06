"""
TradeAlpha.app Multi-Number OTP Automation
- Reads numbers from n.txt (format: countrycode + local, e.g., 255674162580)
- Parses country code and local number
- Selects country from dropdown using the visible +255 text
- Fills local number and submits
- Handles "Failed to send verification code" error
- First time: manual OTP entry, saves session on success
- Subsequent runs: headless using saved session
"""

import os
import time
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ================= CONFIGURATION =================
NUMBERS_FILE = "n.txt"
STATE_DIR = "auth_states"
SITE_URL = "https://www.tradealpha.app"
DELAY_BETWEEN_NUMBERS = 10  # seconds (be respectful)
RETRY_DELAY = 60            # seconds to wait after error before next number (if needed)

# ---------- SELECTORS (based on your screenshots) ----------
COUNTRY_TRIGGER = "div.selected-country"          # Element showing current code (e.g., "+1")
# After clicking trigger, options have text like "Tanzania +255"
PHONE_INPUT = "input[placeholder*='phone']"       # Input for local number
CLAIM_BUTTON = "button:has-text('Claim')"         # "Claim your early access spot" button
OTP_HEADING = "text='Enter verification code'"    # Heading on OTP page
ERROR_MESSAGE = "text='Failed to send verification code'"  # Error message after failed send
# ========================================================

os.makedirs(STATE_DIR, exist_ok=True)

def parse_phone(full_number):
    """
    Split full number (e.g., '255674162580') into country_code and local_number.
    """
    # Common country codes (add more if needed)
    country_codes = ["255", "1", "44", "886", "992", "66", "670", "690", "228", "233"]
    for code in sorted(country_codes, key=len, reverse=True):
        if full_number.startswith(code):
            local = full_number[len(code):]
            return code, local
    raise ValueError(f"Unknown country code in {full_number}")

def get_state_file(phone):
    """Return filename for session state."""
    safe = phone.replace("+", "").strip()
    return os.path.join(STATE_DIR, f"auth_{safe}.json")

def select_country(page, country_code):
    """
    Open country dropdown and click the option containing '+{country_code}'.
    """
    page.click(COUNTRY_TRIGGER)
    page.wait_for_selector(f"text='+{country_code}'")
    page.click(f"text='+{country_code}'")
    time.sleep(0.5)  # UI update delay

def process_number(full_number):
    """Handle one phone number."""
    try:
        country_code, local_number = parse_phone(full_number)
    except ValueError as e:
        print(f"❌ {e}")
        return

    state_file = get_state_file(full_number)
    session_exists = os.path.exists(state_file)

    with sync_playwright() as p:
        # Launch visible browser for first-time setup or error recovery, headless for subsequent runs
        headless_mode = session_exists  # if we have a session, try headless first
        browser = p.chromium.launch(headless=headless_mode)
        
        if session_exists:
            context = browser.new_context(storage_state=state_file)
            print(f"📂 Loaded session for {full_number}")
        else:
            context = browser.new_context()
            print(f"🆕 First time for {full_number} (country: {country_code}, local: {local_number})")

        page = context.new_page()
        page.goto(SITE_URL)

        # ---------- LOGIN FLOW ----------
        if session_exists:
            # Verify we're still logged in
            try:
                # If we see OTP page or error, session is stale
                page.wait_for_selector(OTP_HEADING, timeout=3000)
                print(f"⚠️  Session expired for {full_number}, removing state file.")
                os.remove(state_file)
                browser.close()
                # Re-run this number in visible mode
                process_number(full_number)
                return
            except PlaywrightTimeoutError:
                try:
                    page.wait_for_selector(ERROR_MESSAGE, timeout=2000)
                    print(f"⚠️  Session expired (error detected) for {full_number}, removing state file.")
                    os.remove(state_file)
                    browser.close()
                    process_number(full_number)
                    return
                except PlaywrightTimeoutError:
                    # No OTP page or error, assume logged in
                    print(f"✅ Authenticated with saved session for {full_number}")
                    # You can add post-login assertions here
                    browser.close()
                    return
        else:
            # ----- First time: manual OTP -----
            # 1. Select country
            try:
                select_country(page, country_code)
            except Exception as e:
                print(f"❌ Failed to select country: {e}")
                browser.close()
                return

            # 2. Enter local phone number
            phone_field = page.locator(PHONE_INPUT)
            phone_field.fill(local_number)

            # 3. Click Claim button
            claim_btn = page.locator(CLAIM_BUTTON)
            claim_btn.click()

            # 4. Wait for either OTP page or error message
            print(f"⏳ Waiting for response...")
            try:
                # Wait up to 10 seconds for either OTP heading or error
                page.wait_for_selector(OTP_HEADING, timeout=10000)
                print("✅ OTP page loaded. Enter the 6-digit code manually in the browser.")
                print("⏱️  You have 60 seconds to complete OTP...")
                
                # Wait for OTP verification to complete (you need to identify a post-login element)
                # For now, we wait for the OTP heading to disappear (indicating code entered)
                try:
                    page.wait_for_function(
                        "!document.querySelector('text=\"Enter verification code\"')",
                        timeout=60000
                    )
                    print(f"✅ OTP verified for {full_number}")
                    
                    # Save the authenticated session
                    context.storage_state(path=state_file)
                    print(f"💾 Session saved to {state_file}")
                except PlaywrightTimeoutError:
                    print(f"❌ OTP verification timed out for {full_number}")
            except PlaywrightTimeoutError:
                # Check if error message appeared
                try:
                    page.wait_for_selector(ERROR_MESSAGE, timeout=2000)
                    print(f"❌ Failed to send verification code for {full_number}. Skipping.")
                    # Optionally take a screenshot for debugging
                    page.screenshot(path=f"error_{full_number}.png")
                except PlaywrightTimeoutError:
                    print(f"❓ Unknown response after submission for {full_number}. Check manually.")
                    page.screenshot(path=f"unknown_{full_number}.png")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")

            browser.close()

def main():
    try:
        with open(NUMBERS_FILE, "r") as f:
            numbers = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ File {NUMBERS_FILE} not found. Create it with one number per line.")
        return

    print(f"📞 Loaded {len(numbers)} numbers from {NUMBERS_FILE}")
    for i, num in enumerate(numbers, 1):
        print(f"\n--- Processing {i}/{len(numbers)}: {num} ---")
        process_number(num)
        if i < len(numbers):
            print(f"⏳ Waiting {DELAY_BETWEEN_NUMBERS}s...")
            time.sleep(DELAY_BETWEEN_NUMBERS)

    print("\n✅ Done.")

if __name__ == "__main__":
    main()
