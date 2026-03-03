from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import logging
import os
from datetime import datetime
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('otp_test_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EntryWalaOTPTester:
    def __init__(self, headless=False):
        """Initialize the Firefox browser driver"""
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        
        # Add user agent to appear more like a real browser
        options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0")
        
        if headless:
            options.add_argument('--headless')
        
        # Auto-manage GeckoDriver (Firefox driver)
        service = Service(GeckoDriverManager().install())
        self.driver = webdriver.Firefox(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 15)
        
        # Results tracking with country info
        self.results = {
            'successful': [],
            'failed': [],
            'invalid': [],
            'otp_received': []
        }
        
        # Country codes mapping
        self.country_codes = {
            '255': 'Tanzania', '60': 'Malaysia', '91': 'India', '244': 'Angola',
            '44': 'United Kingdom', '1': 'USA/Canada', '234': 'Nigeria',
            '27': 'South Africa', '92': 'Pakistan', '880': 'Bangladesh',
            '254': 'Kenya', '256': 'Uganda', '20': 'Egypt', '966': 'Saudi Arabia',
            '971': 'UAE', '966': 'Saudi Arabia', '974': 'Qatar', '965': 'Kuwait',
            '968': 'Oman', '973': 'Bahrain', '962': 'Jordan', '961': 'Lebanon'
        }
    
    def detect_country(self, phone_number):
        """Detect country from phone number"""
        cleaned = re.sub(r'\D', '', phone_number)
        
        # Try to match country codes (longest first)
        for code_len in [3, 2, 1]:
            if len(cleaned) >= code_len:
                potential_code = cleaned[:code_len]
                if potential_code in self.country_codes:
                    return self.country_codes[potential_code], potential_code
        
        # Special handling for common codes
        if cleaned.startswith('255'):
            return 'Tanzania', '255'
        elif cleaned.startswith('60'):
            return 'Malaysia', '60'
        elif cleaned.startswith('91'):
            return 'India', '91'
        elif cleaned.startswith('1'):
            return 'USA/Canada', '1'
        elif cleaned.startswith('44'):
            return 'United Kingdom', '44'
        
        return 'Unknown', '??'
    
    def read_phone_numbers(self, filename='n.txt'):
        """Read phone numbers from file and detect countries"""
        try:
            with open(filename, 'r') as file:
                numbers = []
                countries = defaultdict(int)
                
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract only digits
                        digits = re.sub(r'\D', '', line)
                        
                        if digits:  # Only process if we have digits
                            # Detect country
                            country, code = self.detect_country(digits)
                            countries[country] += 1
                            
                            # Take last 10 digits for EntryWala
                            ten_digit = digits[-10:] if len(digits) > 10 else digits
                            
                            numbers.append({
                                'original': line,
                                'full_digits': digits,
                                'cleaned': ten_digit,
                                'country': country,
                                'country_code': code
                            })
                            
                            if len(digits) > 10:
                                logger.info(f"Trimmed {digits} ({country}) to 10 digits: {ten_digit}")
            
            logger.info(f"✅ Loaded {len(numbers)} phone numbers from {filename}")
            
            # Show country breakdown
            if numbers:
                logger.info("\n🌍 Country Distribution:")
                for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"  {country}: {count} numbers")
                
                logger.info("\n📱 First 5 numbers:")
                for num in numbers[:5]:
                    logger.info(f"  • {num['original']} → {num['country']} (+{num['country_code']}) → 10-digit: {num['cleaned']}")
            
            return numbers
        except FileNotFoundError:
            logger.error(f"❌ File {filename} not found!")
            return []
        except Exception as e:
            logger.error(f"❌ Error reading file: {str(e)}")
            return []
    
    def find_phone_input(self):
        """Find the phone number input field - matching your screenshot"""
        selectors = [
            (By.XPATH, "//input[@placeholder='Phone number']"),
            (By.XPATH, "//input[contains(@placeholder, '10-digit')]"),
            (By.CSS_SELECTOR, "input[placeholder*='phone' i]"),
            (By.CSS_SELECTOR, "input[type='tel']"),
            (By.XPATH, "//label[contains(text(), 'Phone')]/following::input[1]"),
            (By.CSS_SELECTOR, "input[name*='phone' i]"),
            (By.CSS_SELECTOR, "input[id*='phone' i]"),
        ]
        
        for by, selector in selectors:
            try:
                element = self.driver.find_element(by, selector)
                if element.is_displayed():
                    logger.info(f"✅ Found phone input field")
                    return element
            except:
                continue
        
        # If still not found, try to find any text input near "phone" text
        try:
            elements = self.driver.find_elements(By.TAG_NAME, "input")
            for element in elements:
                if element.is_displayed() and element.get_attribute('type') in ['text', 'tel', 'number']:
                    # Check if there's "phone" text nearby
                    page_text = self.driver.page_source.lower()
                    if 'phone' in page_text:
                        logger.info(f"✅ Found likely phone input (input type: {element.get_attribute('type')})")
                        return element
        except:
            pass
        
        return None
    
    def find_consent_checkbox(self):
        """Find the consent checkbox - matching your screenshot"""
        selectors = [
            (By.XPATH, "//input[@type='checkbox']"),
            (By.XPATH, "//label[contains(text(), 'authorize')]/preceding::input[1]"),
            (By.XPATH, "//label[contains(text(), 'I authorize')]/preceding::input[1]"),
            (By.CSS_SELECTOR, "input[type='checkbox']"),
        ]
        
        for by, selector in selectors:
            try:
                checkbox = self.driver.find_element(by, selector)
                if checkbox.is_displayed() and not checkbox.is_selected():
                    logger.info("✅ Found consent checkbox")
                    return checkbox
            except:
                continue
        return None
    
    def find_submit_button(self):
        """Find the send verification code button - EXACT match from your screenshot"""
        selectors = [
            # EXACT text match from your screenshot
            (By.XPATH, "//button[text()='Send verification code']"),
            (By.XPATH, "//button[contains(text(), 'Send verification code')]"),
            (By.XPATH, "//button[contains(text(), 'Send') and contains(text(), 'verification')]"),
            (By.XPATH, "//button[contains(text(), 'Send')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, ".btn-primary"),
            (By.XPATH, "//form//button"),
        ]
        
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        button_text = element.text.strip()
                        logger.info(f"✅ Found submit button: '{button_text}'")
                        return element
            except:
                continue
        
        # Debug: list all buttons if not found
        logger.info("🔍 Could not find button. Listing all buttons on page:")
        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
        for i, btn in enumerate(all_buttons):
            if btn.is_displayed():
                logger.info(f"   Button {i}: text='{btn.text}', class='{btn.get_attribute('class')}'")
        
        return None
    
    def is_otp_screen(self):
        """Check if we're on the OTP verification screen - matching your screenshot"""
        indicators = [
            "verification code sent to",
            "enter the verification code",
            "didn't receive the code",
            "resend in",
            "verification code"
        ]
        
        page_text = self.driver.page_source.lower()
        for indicator in indicators:
            if indicator in page_text:
                return True
        
        # Check for 6 OTP input boxes
        try:
            otp_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'][maxlength='1']")
            if len(otp_inputs) == 6:
                return True
        except:
            pass
        
        return False
    
    def get_displayed_number(self):
        """Get the phone number displayed on OTP screen"""
        try:
            elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'sent to')]")
            for element in elements:
                text = element.text
                digits = re.sub(r'\D', '', text)
                if len(digits) >= 10:
                    return digits[-10:]
        except:
            pass
        return None
    
    def wait_for_otp_screen(self, timeout=20):
        """Wait for OTP screen to appear"""
        logger.info("⏳ Waiting for OTP screen...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_otp_screen():
                logger.info("✅ OTP verification screen detected!")
                
                # Take screenshot
                screenshot = f"otp_screen_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot)
                logger.info(f"📸 Screenshot saved: {screenshot}")
                
                # Get displayed number
                displayed = self.get_displayed_number()
                if displayed:
                    logger.info(f"📱 OTP sent to: {displayed}")
                
                return True
            
            time.sleep(1)
        
        logger.warning("⚠️ OTP screen did not appear within timeout")
        return False
    
    def submit_phone_number(self, phone_data):
        """Submit a phone number on the website"""
        phone = phone_data['cleaned']
        country = phone_data['country']
        
        try:
            logger.info(f"\n📱 Testing: {phone} ({country})")
            
            # Find phone input
            phone_input = self.find_phone_input()
            if not phone_input:
                logger.error("❌ Could not find phone input field")
                return False
            
            # Clear and enter number
            phone_input.clear()
            phone_input.send_keys(phone)
            logger.info(f"✅ Entered phone number: {phone}")
            time.sleep(2)
            
            # Find and check consent checkbox
            checkbox = self.find_consent_checkbox()
            if checkbox:
                try:
                    checkbox.click()
                    logger.info("✅ Checked consent box")
                except:
                    self.driver.execute_script("arguments[0].click();", checkbox)
                    logger.info("✅ Checked consent box (via JavaScript)")
                time.sleep(1)
            
            # Find and click submit button
            submit_btn = self.find_submit_button()
            if not submit_btn:
                logger.error("❌ Could not find submit button")
                return False
            
            # Scroll to button and click
            self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(1)
            
            try:
                submit_btn.click()
                logger.info("✅ Clicked 'Send verification code' button")
            except:
                self.driver.execute_script("arguments[0].click();", submit_btn)
                logger.info("✅ Clicked button via JavaScript")
            
            # Wait for OTP screen
            return self.wait_for_otp_screen()
            
        except Exception as e:
            logger.error(f"❌ Error: {str(e)}")
            return False
    
    def navigate_back(self):
        """Navigate back to phone entry screen"""
        logger.info("\n🔄 Preparing for next number...")
        
        try:
            # Look for "Change number" link
            change_links = [
                (By.XPATH, "//*[contains(text(), 'Change number')]"),
                (By.XPATH, "//*[contains(text(), 'Change')]"),
                (By.XPATH, "//*[contains(text(), 'Back')]"),
            ]
            
            for by, selector in change_links:
                try:
                    element = self.driver.find_element(by, selector)
                    element.click()
                    logger.info("✅ Clicked 'Change number'")
                    time.sleep(3)
                    return
                except:
                    continue
            
            # If no link found, just go back
            self.driver.back()
            logger.info("⬅️ Navigated back")
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)
            
        except Exception as e:
            logger.warning(f"⚠️ Navigation issue: {str(e)}")
            self.driver.refresh()
            time.sleep(3)
    
    def run_test(self):
        """Main test execution"""
        # Read numbers
        numbers = self.read_phone_numbers()
        if not numbers:
            logger.error("❌ No phone numbers to test!")
            return
        
        # Open registration page
        logger.info("\n🚀 Opening EntryWala registration page...")
        self.driver.get("https://entrywala.com/register")
        time.sleep(5)
        
        # Save initial screenshot
        self.driver.save_screenshot("initial_page.png")
        logger.info("📸 Initial page screenshot saved")
        
        # Process each number
        for i, phone_data in enumerate(numbers, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"TEST {i}/{len(numbers)}")
            logger.info(f"Number: {phone_data['original']}")
            logger.info(f"Country: {phone_data['country']} (+{phone_data['country_code']})")
            logger.info(f"10-digit: {phone_data['cleaned']}")
            logger.info(f"{'='*60}")
            
            # Submit number
            success = self.submit_phone_number(phone_data)
            
            if success:
                logger.info(f"✅ SUCCESS: OTP screen reached for {phone_data['country']}")
                self.results['successful'].append((
                    phone_data['original'],
                    phone_data['country'],
                    phone_data['country_code']
                ))
            else:
                logger.error(f"❌ FAILED for {phone_data['country']}")
                self.results['failed'].append((
                    phone_data['original'],
                    phone_data['country'],
                    phone_data['country_code']
                ))
            
            # Navigate back for next number
            if i < len(numbers):
                wait_time = 15
                logger.info(f"⏱️  Waiting {wait_time} seconds...")
                
                for remaining in range(wait_time, 0, -1):
                    print(f"\rNext in: {remaining:2d}s", end="", flush=True)
                    time.sleep(1)
                print("\r" + " " * 20, end="\r")
                
                self.navigate_back()
        
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        logger.info("\n" + "="*70)
        logger.info("📊 FINAL RESULTS")
        logger.info("="*70)
        
        # Country stats
        country_stats = defaultdict(lambda: {'success': 0, 'failed': 0})
        
        for num, country, code in self.results['successful']:
            country_stats[country]['success'] += 1
        
        for num, country, code in self.results['failed']:
            country_stats[country]['failed'] += 1
        
        # Print by country
        logger.info("\n🌍 RESULTS BY COUNTRY:")
        logger.info("-" * 50)
        for country, stats in sorted(country_stats.items(), key=lambda x: x[1]['success'], reverse=True):
            total = stats['success'] + stats['failed']
            rate = (stats['success'] / total * 100) if total > 0 else 0
            logger.info(f"{country:20} | ✅ {stats['success']:2} | ❌ {stats['failed']:2} | Rate: {rate:5.1f}%")
        
        # Overall
        total_success = len(self.results['successful'])
        total_failed = len(self.results['failed'])
        total = total_success + total_failed
        
        logger.info("\n" + "="*70)
        logger.info(f"✅ Successful: {total_success}")
        logger.info(f"❌ Failed: {total_failed}")
        logger.info(f"📊 Success Rate: {(total_success/total*100):.1f}%")
        logger.info("="*70)
        
        # Save detailed report
        self.save_report()
    
    def save_report(self):
        """Save detailed report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"otp_report_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("ENTRYWALA OTP TEST REPORT\n")
            f.write("="*50 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("SUCCESSFUL:\n")
            for num, country, code in self.results['successful']:
                f.write(f"  ✅ {num} ({country})\n")
            
            f.write("\nFAILED:\n")
            for num, country, code in self.results['failed']:
                f.write(f"  ❌ {num} ({country})\n")
        
        logger.info(f"\n📁 Report saved: {filename}")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()
        logger.info("✅ Browser closed")

def main():
    """Main function"""
    print("""
    ╔════════════════════════════════════════════╗
    ║    ENTRYWALA OTP TESTER - FINAL VERSION    ║
    ║        https://entrywala.com/register      ║
    ╚════════════════════════════════════════════╝
    """)
    
    # Check for n.txt
    if not os.path.exists('n.txt'):
        print("\n📝 Creating sample n.txt file...")
        with open('n.txt', 'w') as f:
            f.write("255775778626  # Tanzania\n")
            f.write("60103251261   # Malaysia\n")
            f.write("9848412345    # India\n")
        print("✅ Created n.txt with sample numbers")
    
    # Preview numbers
    preview = EntryWalaOTPTester(headless=True)
    numbers = preview.read_phone_numbers()
    preview.close()
    
    if not numbers:
        return
    
    # Get user choice
    print(f"\n📱 Found {len(numbers)} numbers in n.txt")
    headless = input("\n🖥️  Run in background? (y/n, default n): ").lower() == 'y'
    
    # Run test
    tester = EntryWalaOTPTester(headless=headless)
    
    try:
        tester.run_test()
        if not headless:
            input("\nPress Enter to close browser...")
    except KeyboardInterrupt:
        logger.info("\n⚠️ Test interrupted")
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
    finally:
        tester.close()

if __name__ == "__main__":
    main()
