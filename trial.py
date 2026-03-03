from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
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
            'successful': [],  # Will store tuples of (number, country, country_code)
            'failed': [],      # Will store tuples of (number, country, country_code)
            'invalid': [],     # Will store tuples of (number, reason)
            'otp_received': [] # Will store tuples of (number, country, country_code)
        }
        
        # Country codes mapping
        self.country_codes = {
            # Africa
            '93': 'Afghanistan', '355': 'Albania', '213': 'Algeria', '376': 'Andorra', '244': 'Angola',
            '54': 'Argentina', '374': 'Armenia', '297': 'Aruba', '61': 'Australia', '43': 'Austria',
            '994': 'Azerbaijan', '973': 'Bahrain', '880': 'Bangladesh', '375': 'Belarus', '32': 'Belgium',
            '501': 'Belize', '229': 'Benin', '975': 'Bhutan', '591': 'Bolivia', '387': 'Bosnia',
            '267': 'Botswana', '55': 'Brazil', '673': 'Brunei', '359': 'Bulgaria', '226': 'Burkina Faso',
            '257': 'Burundi', '855': 'Cambodia', '237': 'Cameroon', '1': 'Canada/USA', '238': 'Cape Verde',
            '236': 'Central African Republic', '235': 'Chad', '56': 'Chile', '86': 'China', '57': 'Colombia',
            '269': 'Comoros', '242': 'Congo', '243': 'DR Congo', '506': 'Costa Rica', '225': 'Ivory Coast',
            '385': 'Croatia', '53': 'Cuba', '357': 'Cyprus', '420': 'Czech Republic', '45': 'Denmark',
            '253': 'Djibouti', '593': 'Ecuador', '20': 'Egypt', '503': 'El Salvador', '240': 'Equatorial Guinea',
            '291': 'Eritrea', '372': 'Estonia', '251': 'Ethiopia', '679': 'Fiji', '358': 'Finland',
            '33': 'France', '241': 'Gabon', '220': 'Gambia', '995': 'Georgia', '49': 'Germany',
            '233': 'Ghana', '30': 'Greece', '299': 'Greenland', '502': 'Guatemala', '224': 'Guinea',
            '245': 'Guinea-Bissau', '592': 'Guyana', '509': 'Haiti', '504': 'Honduras', '852': 'Hong Kong',
            '36': 'Hungary', '354': 'Iceland', '91': 'India', '62': 'Indonesia', '98': 'Iran',
            '964': 'Iraq', '353': 'Ireland', '972': 'Israel', '39': 'Italy', '81': 'Japan',
            '962': 'Jordan', '7': 'Kazakhstan', '254': 'Kenya', '686': 'Kiribati', '965': 'Kuwait',
            '996': 'Kyrgyzstan', '856': 'Laos', '371': 'Latvia', '961': 'Lebanon', '266': 'Lesotho',
            '231': 'Liberia', '218': 'Libya', '423': 'Liechtenstein', '370': 'Lithuania', '352': 'Luxembourg',
            '853': 'Macau', '389': 'North Macedonia', '261': 'Madagascar', '265': 'Malawi', '60': 'Malaysia',
            '960': 'Maldives', '223': 'Mali', '356': 'Malta', '692': 'Marshall Islands', '222': 'Mauritania',
            '230': 'Mauritius', '52': 'Mexico', '691': 'Micronesia', '373': 'Moldova', '377': 'Monaco',
            '976': 'Mongolia', '382': 'Montenegro', '212': 'Morocco', '258': 'Mozambique', '95': 'Myanmar',
            '264': 'Namibia', '674': 'Nauru', '977': 'Nepal', '31': 'Netherlands', '64': 'New Zealand',
            '505': 'Nicaragua', '227': 'Niger', '234': 'Nigeria', '683': 'Niue', '850': 'North Korea',
            '47': 'Norway', '968': 'Oman', '92': 'Pakistan', '680': 'Palau', '507': 'Panama',
            '675': 'Papua New Guinea', '595': 'Paraguay', '51': 'Peru', '63': 'Philippines', '48': 'Poland',
            '351': 'Portugal', '974': 'Qatar', '40': 'Romania', '7': 'Russia', '250': 'Rwanda',
            '590': 'Saint Barthélemy', '685': 'Samoa', '378': 'San Marino', '239': 'Sao Tome', '966': 'Saudi Arabia',
            '221': 'Senegal', '381': 'Serbia', '248': 'Seychelles', '232': 'Sierra Leone', '65': 'Singapore',
            '421': 'Slovakia', '386': 'Slovenia', '677': 'Solomon Islands', '252': 'Somalia', '27': 'South Africa',
            '82': 'South Korea', '211': 'South Sudan', '34': 'Spain', '94': 'Sri Lanka', '249': 'Sudan',
            '597': 'Suriname', '268': 'Eswatini', '46': 'Sweden', '41': 'Switzerland', '963': 'Syria',
            '886': 'Taiwan', '992': 'Tajikistan', '255': 'Tanzania', '66': 'Thailand', '670': 'Timor-Leste',
            '228': 'Togo', '690': 'Tokelau', '676': 'Tonga', '216': 'Tunisia', '90': 'Turkey',
            '993': 'Turkmenistan', '688': 'Tuvalu', '256': 'Uganda', '380': 'Ukraine', '971': 'UAE',
            '44': 'United Kingdom', '598': 'Uruguay', '998': 'Uzbekistan', '678': 'Vanuatu',
            '379': 'Vatican City', '58': 'Venezuela', '84': 'Vietnam', '681': 'Wallis and Futuna',
            '967': 'Yemen', '260': 'Zambia', '263': 'Zimbabwe'
        }
        
    def detect_country(self, phone_number):
        """Detect country from phone number"""
        # Clean the number
        cleaned = re.sub(r'\D', '', phone_number)
        
        # Try to match country codes (longest first)
        for code_len in [3, 2, 1]:
            if len(cleaned) >= code_len:
                potential_code = cleaned[:code_len]
                if potential_code in self.country_codes:
                    return self.country_codes[potential_code], potential_code
        
        # Special handling for common codes
        if cleaned.startswith('1'):
            return 'USA/Canada', '1'
        elif cleaned.startswith('44'):
            return 'United Kingdom', '44'
        elif cleaned.startswith('91'):
            return 'India', '91'
        elif cleaned.startswith('255'):
            return 'Tanzania', '255'
        elif cleaned.startswith('92'):
            return 'Pakistan', '92'
        elif cleaned.startswith('880'):
            return 'Bangladesh', '880'
        elif cleaned.startswith('234'):
            return 'Nigeria', '234'
        elif cleaned.startswith('27'):
            return 'South Africa', '27'
        elif cleaned.startswith('20'):
            return 'Egypt', '20'
        elif cleaned.startswith('254'):
            return 'Kenya', '254'
        elif cleaned.startswith('256'):
            return 'Uganda', '256'
        
        return 'Unknown', '??'
    
    def read_phone_numbers(self, filename='n.txt'):
        """Read phone numbers from file and detect countries"""
        try:
            with open(filename, 'r') as file:
                numbers = []
                countries = defaultdict(int)
                
                for line in file:
                    line = line.strip()
                    if line:
                        # Extract only digits
                        digits = re.sub(r'\D', '', line)
                        
                        # Store original and cleaned
                        country, code = self.detect_country(digits)
                        countries[country] += 1
                        
                        # Take last 10 digits if number is longer (for EntryWala)
                        if len(digits) > 10:
                            original = digits
                            digits = digits[-10:]
                            logger.info(f"Trimmed {original} ({country}) to 10 digits: {digits}")
                        
                        numbers.append({
                            'original': line,
                            'cleaned': digits,
                            'country': country,
                            'country_code': code,
                            'full_number': line
                        })
            
            logger.info(f"Loaded {len(numbers)} phone numbers from {filename}")
            
            # Show country breakdown
            logger.info("\n🌍 Country Distribution:")
            for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {country}: {count} numbers")
            
            # Show first few numbers with countries
            logger.info("\nFirst 5 numbers with country detection:")
            for num in numbers[:5]:
                logger.info(f"  • {num['original']} → {num['country']} (Code: +{num['country_code']})")
            
            return numbers
        except FileNotFoundError:
            logger.error(f"File {filename} not found!")
            return []
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return []
    
    def validate_phone_number(self, phone_data):
        """Validate 10-digit phone number"""
        cleaned = phone_data['cleaned']
        
        if len(cleaned) == 10:
            return True
        else:
            logger.warning(f"Invalid length ({len(cleaned)} digits) for {phone_data['original']} - needs exactly 10 digits")
            return False
    
    def find_phone_input(self):
        """Find the phone number input field"""
        selectors = [
            (By.XPATH, "//input[@placeholder='Phone number']"),
            (By.XPATH, "//input[contains(@placeholder, '10-digit')]"),
            (By.CSS_SELECTOR, "input[placeholder*='phone' i]"),
            (By.CSS_SELECTOR, "input[name*='phone' i]"),
            (By.CSS_SELECTOR, "input[id*='phone' i]"),
            (By.CSS_SELECTOR, "input[type='tel']"),
            (By.XPATH, "//label[contains(text(), 'Phone')]/following::input[1]"),
        ]
        
        for by, selector in selectors:
            try:
                element = self.driver.find_element(by, selector)
                if element.is_displayed():
                    logger.info(f"Found phone input field")
                    return element
            except:
                continue
        return None
    
    def find_submit_button(self):
        """Find the send verification code button"""
        selectors = [
            (By.XPATH, "//button[contains(text(), 'Send verification code')]"),
            (By.XPATH, "//button[contains(text(), 'Send')]"),
            (By.XPATH, "//button[contains(text(), 'Continue')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, ".btn-primary"),
        ]
        
        for by, selector in selectors:
            try:
                element = self.driver.find_element(by, selector)
                if element.is_displayed() and element.is_enabled():
                    logger.info(f"Found submit button")
                    return element
            except:
                continue
        return None
    
    def check_consent_checkbox(self):
        """Find and check the consent checkbox"""
        selectors = [
            (By.XPATH, "//input[@type='checkbox']"),
            (By.XPATH, "//label[contains(text(), 'authorize')]/preceding::input[1]"),
            (By.XPATH, "//label[contains(text(), 'I authorize')]/preceding::input[1]"),
            (By.CSS_SELECTOR, ".consent-checkbox"),
        ]
        
        for by, selector in selectors:
            try:
                checkbox = self.driver.find_element(by, selector)
                if checkbox.is_displayed() and not checkbox.is_selected():
                    try:
                        checkbox.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", checkbox)
                    logger.info("✓ Consent checkbox checked")
                    time.sleep(1)
                    return True
            except:
                continue
        return False
    
    def is_otp_screen(self):
        """Check if we're on the OTP verification screen"""
        otp_indicators = [
            "verification code sent",
            "verification code",
            "enter the verification code",
            "didn't receive the code",
            "resend in",
            "otp"
        ]
        
        page_text = self.driver.page_source.lower()
        for indicator in otp_indicators:
            if indicator in page_text:
                return True
        
        # Check for OTP input fields (usually 6 boxes)
        try:
            otp_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text'][maxlength='1']")
            if len(otp_inputs) >= 4:
                return True
        except:
            pass
            
        return False
    
    def get_displayed_number(self):
        """Get the phone number displayed on OTP screen"""
        try:
            selectors = [
                (By.XPATH, "//*[contains(text(), 'sent to')]/following::*[1]"),
                (By.CSS_SELECTOR, ".phone-number"),
                (By.XPATH, "//strong[contains(text(), 'sent to')]/.."),
            ]
            
            for by, selector in selectors:
                try:
                    element = self.driver.find_element(by, selector)
                    text = element.text
                    digits = re.sub(r'\D', '', text)
                    if len(digits) >= 10:
                        return digits[-10:]
                except:
                    continue
        except:
            pass
        return None
    
    def wait_for_otp_screen(self, timeout=15):
        """Wait for OTP screen to appear"""
        logger.info("Waiting for OTP screen...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_otp_screen():
                logger.info("✓ OTP verification screen detected!")
                
                displayed_num = self.get_displayed_number()
                if displayed_num:
                    logger.info(f"OTP sent to: {displayed_num}")
                
                screenshot = f"otp_screen_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot)
                logger.info(f"OTP screen screenshot saved: {screenshot}")
                
                return True
            time.sleep(1)
        
        logger.warning("OTP screen did not appear within timeout")
        return False
    
    def submit_phone_number(self, phone_data):
        """Submit a phone number on the website"""
        phone = phone_data['cleaned']
        country = phone_data['country']
        country_code = phone_data['country_code']
        
        try:
            logger.info(f"\n📱 Testing: {phone}")
            logger.info(f"🌍 Country: {country} (+{country_code})")
            
            # Find phone input field
            phone_input = self.find_phone_input()
            if not phone_input:
                logger.error("Could not find phone input field")
                return False
            
            # Clear and enter phone number
            phone_input.clear()
            phone_input.send_keys(phone)
            logger.info(f"Entered phone number: {phone}")
            
            time.sleep(2)
            
            # Check and check consent box if present
            self.check_consent_checkbox()
            
            # Find and click submit button
            submit_btn = self.find_submit_button()
            if not submit_btn:
                logger.error("Could not find submit button")
                return False
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", submit_btn)
            logger.info("Clicked send verification code button")
            
            # Wait and check for OTP screen
            if self.wait_for_otp_screen():
                logger.info(f"✅ OTP screen appeared for {country} number: {phone}")
                return True
            else:
                logger.error(f"❌ OTP screen did not appear for {country} number: {phone}")
                return False
            
        except Exception as e:
            logger.error(f"Error submitting phone number: {str(e)}")
            return False
    
    def run_test(self):
        """Main test execution"""
        # Read phone numbers with country detection
        numbers = self.read_phone_numbers()
        if not numbers:
            logger.error("No phone numbers to test!")
            return
        
        # Open the website
        logger.info("\n🚀 Opening EntryWala website...")
        self.driver.get("https://www.entrywala.com")
        
        # Wait for page to load
        time.sleep(5)
        
        # Take screenshot of initial page
        self.driver.save_screenshot("initial_page.png")
        logger.info("Initial page screenshot saved as 'initial_page.png'")
        
        # Process each number
        for i, phone_data in enumerate(numbers, 1):
            logger.info(f"\n{'='*70}")
            logger.info(f"TEST {i}/{len(numbers)}")
            logger.info(f"Number: {phone_data['original']}")
            logger.info(f"Country: {phone_data['country']} (+{phone_data['country_code']})")
            logger.info(f"10-digit format: {phone_data['cleaned']}")
            logger.info(f"{'='*70}")
            
            # Validate phone number
            if not self.validate_phone_number(phone_data):
                logger.warning(f"Invalid phone number: {phone_data['original']}")
                self.results['invalid'].append((
                    phone_data['original'],
                    phone_data['country'],
                    phone_data['country_code'],
                    "Invalid format"
                ))
                continue
            
            # Submit phone number
            success = self.submit_phone_number(phone_data)
            
            if success:
                logger.info(f"✅ SUCCESS: OTP screen reached for {phone_data['country']} number")
                self.results['successful'].append((
                    phone_data['original'],
                    phone_data['country'],
                    phone_data['country_code']
                ))
                self.results['otp_received'].append((
                    phone_data['original'],
                    phone_data['country'],
                    phone_data['country_code']
                ))
            else:
                logger.error(f"❌ FAILED: Could not get OTP for {phone_data['country']} number")
                self.results['failed'].append((
                    phone_data['original'],
                    phone_data['country'],
                    phone_data['country_code']
                ))
            
            # Navigate back for next number
            if i < len(numbers):
                self.navigate_back()
        
        # Print summary
        self.print_summary()
    
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
                    logger.info("Clicked 'Change number' link")
                    time.sleep(3)
                    return
                except:
                    continue
            
            # If no link found, just go back
            self.driver.back()
            logger.info("Navigated back")
            time.sleep(3)
            self.driver.refresh()
            time.sleep(3)
            
        except Exception as e:
            logger.warning(f"Could not navigate back: {str(e)}")
            self.driver.refresh()
            time.sleep(3)
        
        # Wait between numbers
        wait_time = 15
        logger.info(f"⏱️  Waiting {wait_time} seconds before next number...")
        for remaining in range(wait_time, 0, -1):
            print(f"\rNext attempt in: {remaining:2d} seconds", end="", flush=True)
            time.sleep(1)
        print("\r" + " " * 40, end="\r")
    
    def print_summary(self):
        """Print test results summary with country breakdown"""
        logger.info("\n" + "="*80)
        logger.info("📊 FINAL TEST SUMMARY BY COUNTRY")
        logger.info("="*80)
        
        # Country statistics
        country_stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'invalid': 0})
        
        for num, country, code in self.results['successful']:
            country_stats[country]['success'] += 1
        
        for num, country, code in self.results['failed']:
            country_stats[country]['failed'] += 1
        
        for num, country, code, reason in self.results['invalid']:
            country_stats[country]['invalid'] += 1
        
        # Print country-wise summary
        logger.info("\n🌍 RESULTS BY COUNTRY:")
        logger.info("-" * 60)
        for country, stats in sorted(country_stats.items(), key=lambda x: x[1]['success'], reverse=True):
            total = stats['success'] + stats['failed'] + stats['invalid']
            success_rate = (stats['success'] / total * 100) if total > 0 else 0
            logger.info(f"{country:25} | ✅ {stats['success']:3} | ❌ {stats['failed']:3} | ⚠️ {stats['invalid']:3} | Success Rate: {success_rate:5.1f}%")
        
        logger.info("\n" + "="*80)
        logger.info("📋 DETAILED RESULTS")
        logger.info("="*80)
        
        # Successful numbers by country
        if self.results['successful']:
            logger.info("\n✅ SUCCESSFUL - OTP SCREEN REACHED:")
            by_country = defaultdict(list)
            for num, country, code in self.results['successful']:
                by_country[country].append((num, code))
            
            for country, numbers in sorted(by_country.items()):
                logger.info(f"\n  {country}:")
                for num, code in numbers:
                    logger.info(f"    • {num} (+{code})")
        
        # Failed numbers by country
        if self.results['failed']:
            logger.info("\n❌ FAILED:")
            by_country = defaultdict(list)
            for num, country, code in self.results['failed']:
                by_country[country].append((num, code))
            
            for country, numbers in sorted(by_country.items()):
                logger.info(f"\n  {country}:")
                for num, code in numbers:
                    logger.info(f"    • {num} (+{code})")
        
        # Invalid numbers
        if self.results['invalid']:
            logger.info("\n⚠️ INVALID NUMBERS:")
            for num, country, code, reason in self.results['invalid']:
                logger.info(f"    • {num} ({country}) - {reason}")
        
        logger.info("\n" + "="*80)
        
        # Save detailed report
        self.save_detailed_report()
    
    def save_detailed_report(self):
        """Save detailed results with country info to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"otp_country_report_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("="*80 + "\n")
            f.write("ENTRYWALA OTP TEST - COUNTRY WISE REPORT\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            # Overall stats
            total = len(self.results['successful']) + len(self.results['failed'])
            f.write(f"Total numbers tested: {total}\n")
            f.write(f"Successful (OTP Screen): {len(self.results['successful'])}\n")
            f.write(f"Failed: {len(self.results['failed'])}\n")
            f.write(f"Invalid: {len(self.results['invalid'])}\n\n")
            
            # Country statistics
            f.write("COUNTRY BREAKDOWN:\n")
            f.write("-" * 60 + "\n")
            
            country_stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'invalid': 0})
            
            for num, country, code in self.results['successful']:
                country_stats[country]['success'] += 1
            
            for num, country, code in self.results['failed']:
                country_stats[country]['failed'] += 1
            
            for num, country, code, reason in self.results['invalid']:
                country_stats[country]['invalid'] += 1
            
            for country, stats in sorted(country_stats.items(), key=lambda x: x[1]['success'], reverse=True):
                total = stats['success'] + stats['failed'] + stats['invalid']
                success_rate = (stats['success'] / total * 100) if total > 0 else 0
                f.write(f"{country:25} | Success: {stats['success']:3} | Failed: {stats['failed']:3} | Invalid: {stats['invalid']:3} | Rate: {success_rate:5.1f}%\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("DETAILED NUMBER LIST:\n")
            f.write("="*80 + "\n\n")
            
            # Group by country for detailed listing
            all_numbers = []
            for num, country, code in self.results['successful']:
                all_numbers.append((num, country, code, "SUCCESS"))
            for num, country, code in self.results['failed']:
                all_numbers.append((num, country, code, "FAILED"))
            for num, country, code, reason in self.results['invalid']:
                all_numbers.append((num, country, code, f"INVALID ({reason})"))
            
            # Sort by country then number
            all_numbers.sort(key=lambda x: (x[1], x[0]))
            
            current_country = None
            for num, country, code, status in all_numbers:
                if country != current_country:
                    f.write(f"\n{country} (+{code}):\n")
                    current_country = country
                f.write(f"  {status:8} : {num}\n")
        
        logger.info(f"\n📁 Detailed country report saved to: {filename}")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()
        logger.info("Browser closed")

def create_sample_file():
    """Create a sample n.txt file with international numbers"""
    sample_numbers = [
        "255677193314",  # Tanzania
        "919876543210",  # India
        "2449967176",    # Angola (from screenshot)
        "447911123456",  # UK
        "14155552671",   # USA
        "234801234567",  # Nigeria
        "27712345678",   # South Africa
        "880171234567",  # Bangladesh
        "254701234567",  # Kenya
        "923001234567",  # Pakistan
    ]
    
    with open('n.txt', 'w') as f:
        for num in sample_numbers:
            f.write(num + '\n')
    
    logger.info("Created sample n.txt file with international numbers")
    logger.info("Each number will be detected by country code")

def main():
    """Main function"""
    print("""
    ╔════════════════════════════════════════════════════╗
    ║     ENTRYWALA OTP TESTING - FIREFOX EDITION       ║
    ║                                                    ║
    ║     Features:                                      ║
    ║     🌍 Auto-detects country from phone number      ║
    ║     🦊 Uses Firefox browser                        ║
    ║     📊 Country-wise success rates                  ║
    ║     📱 Tracks which countries receive OTPs         ║
    ║     📁 Detailed country report                     ║
    ╚════════════════════════════════════════════════════╝
    """)
    
    # Check Firefox version
    print("🔍 Detecting Firefox...")
    
    # Check if n.txt exists
    if not os.path.exists('n.txt'):
        create_sample = input("n.txt not found. Create sample file with international numbers? (y/n): ").lower() == 'y'
        if create_sample:
            create_sample_file()
        else:
            print("Please create n.txt with phone numbers (one per line)")
            return
    
    # Preview numbers with country detection
    print("\n📱 Preview of numbers with country detection:")
    print("-" * 60)
    
    tester_preview = EntryWalaOTPTester(headless=True)
    numbers = tester_preview.read_phone_numbers()
    tester_preview.close()  # Close preview browser
    
    if numbers:
        # Group by country for preview
        preview_counts = defaultdict(int)
        for num in numbers:
            preview_counts[num['country']] += 1
        
        print("\n🌍 Country distribution in your file:")
        for country, count in sorted(preview_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {country}: {count} numbers")
    
    print("\n" + "-" * 60)
    
    # Ask for test parameters
    headless = input("\n🖥️  Run in background (no browser window)? (y/n, default n): ").lower() == 'y'
    delay = input("⏱️  Delay between requests in seconds (default 15): ").strip()
    delay = int(delay) if delay.isdigit() else 15
    
    # Confirm start
    print(f"\n🚀 Starting test with {len(numbers)} numbers from {len(preview_counts)} countries...")
    input("Press Enter to continue or Ctrl+C to cancel...")
    
    # Initialize and run tester
    tester = EntryWalaOTPTester(headless=headless)
    
    try:
        tester.run_test()
        
        if not headless:
            input("\nPress Enter to close browser and exit...")
    
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        tester.close()

if __name__ == "__main__":
    main()
