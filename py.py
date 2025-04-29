import sys
import time
from datetime import datetime
import subprocess
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# === Configuration ===
TEXT_FILE = "FBMemory.txt"
TARGET_URL = "https://www.facebook.com/marketplace/112836245396961"
SEARCH_BOX_XPATH = "//input[@placeholder='Search Marketplace']"
BASH_SCRIPT_PATH = "bashy.sh"  # Path to your bash script

UBLOCK_XPI = "ublock_origin-1.63.2.xpi"
FB_BLOCKER_XPI = "remove_facebook_login_popup-1.0.5.xpi"

def extract_items(driver):
    """Extract item information from the current page"""
    items = []

    # Wait for items to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Marketplace item' or contains(@class, 'x9f619 x78zum5 xdt5ytf')]"))
        )

        # Get all marketplace items on the page
        # Try multiple selectors to catch different item layouts
        marketplace_items = driver.find_elements(By.XPATH, "//div[@aria-label='Marketplace item']")

        # If the above selector doesn't find items, try an alternative
        if not marketplace_items:
            print("Using alternative item selector...")
            marketplace_items = driver.find_elements(By.XPATH, "//a[contains(@href, '/marketplace/item/')]")

        print(f"Found {len(marketplace_items)} potential items on page")

        for item in marketplace_items:
            try:
                # PRICE: Try multiple selectors to find the price
                price = None
                price_elements = item.find_elements(By.XPATH, ".//span[contains(@class, 'x193iq5w') and contains(text(), '$')]")
                if price_elements:
                    price = price_elements[0].text.strip()

                if not price:
                    price_elements = item.find_elements(By.XPATH, ".//*[contains(text(), '$')]")
                    if price_elements:
                        price = price_elements[0].text.strip()

                # NAME: Try multiple selectors for item name
                name = None
                name_elements = item.find_elements(By.XPATH, ".//span[contains(@style, 'line-clamp') or contains(@style, '-webkit-line-clamp')]")
                if name_elements:
                    name = name_elements[0].text.strip()

                if not name:
                    name_elements = item.find_elements(By.XPATH, ".//span[@dir='auto']")
                    for element in name_elements:
                        if '$' not in element.text and element.text.strip():
                            name = element.text.strip()
                            break

                # Get the direct link to the item
                link = item.get_attribute("href")
                if not link:
                    link_element = item.find_element(By.XPATH, ".//a[contains(@href, '/marketplace/item/')]")
                    link = link_element.get_attribute("href")

                # Only add the item if we found at least the name and price
                if name and price:
                    items.append({
                        "name": name,
                        "price": price,
                        "link": link if link else "Link not found"
                    })
                    print(f"Extracted: {name} - {price}")

            except NoSuchElementException as e:
                print(f"Error extracting item: {str(e)}")
                continue
            except Exception as e:
                print(f"Unexpected error extracting item: {str(e)}")
                continue

    except TimeoutException:
        print("Timed out waiting for marketplace items to load")

    return items

def save_to_file(items, search_term):
    """Save the scraped items to a text file and append to master.txt"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"facebook_marketplace_{search_term.replace(' ', '_')}_{timestamp}.txt"
    master_file = "master.txt"

    # Save to individual file
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(f"Search results for: {search_term}\n")
        file.write(f"Total items found: {len(items)}\n")
        file.write("=" * 80 + "\n\n")

        for i, item in enumerate(items, 1):
            file.write(f"Item {i}:\n")
            file.write(f"Name: {item['name']}\n")
            file.write(f"Price: {item['price']}\n")
            file.write(f"Link: {item['link']}\n")
            file.write("-" * 80 + "\n\n")

    # Append to master file
    with open(master_file, 'a', encoding='utf-8') as master:
        master.write(f"\n\nSearch results for: {search_term} (searched on {timestamp})\n")
        master.write(f"Total items found: {len(items)}\n")
        master.write("=" * 80 + "\n\n")

        for i, item in enumerate(items, 1):
            master.write(f"Item {i}:\n")
            master.write(f"Name: {item['name']}\n")
            master.write(f"Price: {item['price']}\n")
            master.write(f"Link: {item['link']}\n")
            master.write("-" * 80 + "\n\n")

    print(f"Data saved to {filename} and appended to {master_file}")
    return filename

# Main execution
options = Options()
options.add_argument('--headless')
service = Service()
driver = webdriver.Firefox(service=service, options=options)

# Install extensions after starting the session
driver.install_addon(UBLOCK_XPI, temporary=True)
driver.install_addon(FB_BLOCKER_XPI, temporary=True)

wait = WebDriverWait(driver, 10)

try:
    # Load all search terms
    with open(TEXT_FILE, "r") as f:
        search_terms = [line.strip() for line in f if line.strip()]

    for term in search_terms:
        print(f"Searching for: {term}")
        driver.get(TARGET_URL)

        # Wait for search box to be present and clickable
        search_box = wait.until(EC.element_to_be_clickable((By.XPATH, SEARCH_BOX_XPATH)))
        search_box.clear()
        search_box.send_keys(term)
        search_box.send_keys(Keys.RETURN)  # Press Enter after typing

        time.sleep(3)  # Wait for results to load

        # Extract items from the search results
        items = extract_items(driver)

        # Save the extracted items to file
        if items:
            save_to_file(items, term)
        else:
            print(f"No items found for search term: {term}")

        time.sleep(1)  # Brief pause before next iteration

finally:
    driver.quit()

# Execute the bash script after all processing is complete
try:
    print(f"Executing bash script: {BASH_SCRIPT_PATH}")
    result = subprocess.run(['bash', BASH_SCRIPT_PATH],
                           check=True,
                           text=True,
                           capture_output=True)
    print(f"Bash script output: {result.stdout}")
    if result.stderr:
        print(f"Bash script errors: {result.stderr}")
except subprocess.CalledProcessError as e:
    print(f"Error executing bash script: {e}")
    print(f"Script output: {e.stdout}")
    print(f"Script errors: {e.stderr}")
except Exception as e:
    print(f"Unexpected error executing bash script: {str(e)}")
