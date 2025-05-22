import os
import re
import time
import requests
import pandas as pd
import argparse
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =============================================================================
#                       COMMAND-LINE ARGUMENT PARSING
# =============================================================================

parser = argparse.ArgumentParser(description="Scrape Census Bureau Working Papers.")
parser.add_argument("--download-files", action="store_true", default=False,
                    help="Download files instead of just collecting links.")
parser.add_argument("--save-interval", type=int, default=10, help="How often (in pages) to save progress.")
parser.add_argument("--output-csv", type=str, default="working_papers_complete.csv",
                    help="Filename for final output CSV.")
parser.add_argument("--temp-csv", type=str, default="temp_output.csv", help="Filename for intermittent save CSV.")
parser.add_argument("--download-dir", type=str, default="downloads", help="Directory to save downloaded files.")
parser.add_argument("--retry-attempts", type=int, default=3, help="Number of times to retry failed requests.")

args = parser.parse_args()

# =============================================================================
#                               CONFIGURATION
# =============================================================================

DOWNLOAD_FILES = args.download_files
SAVE_INTERVAL = args.save_interval
OUTPUT_CSV = args.output_csv
TEMP_CSV = args.temp_csv
DOWNLOAD_DIR = args.download_dir
RETRY_ATTEMPTS = args.retry_attempts  # New retry setting

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".zip"}

# =============================================================================
#                        ENSURE FOLDERS & WEBDRIVER
# =============================================================================

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 5)


# =============================================================================
#                     FUNCTION TO HANDLE STALE ELEMENTS & RETRIES
# =============================================================================

def safe_find_element(driver, by, value, retries=RETRY_ATTEMPTS):
    """Retries finding an element a few times before giving up."""
    for _ in range(retries):
        try:
            return driver.find_element(by, value)
        except:
            time.sleep(1)
    return None


def get_page_data(url, retries=RETRY_ATTEMPTS):
    """Extracts title, downloadable file links, date published, authors, and abstract with retries."""
    for attempt in range(retries):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract the title from the individual paper's page
            title_element = soup.find("h1", class_="cmp-title__text")
            title_text = title_element.text.strip() if title_element else "Title Not Found"

            # Extract file download links
            file_links = [
                urljoin(url, a["href"])
                for a in soup.find_all("a", href=True)
                if any(a["href"].lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)
            ]

            # Extract metadata
            date_element = soup.find("time", {"itemprop": "datePublished"})
            date_published = date_element.text.strip() if date_element else "Unknown"

            author_element = soup.find("div", {"itemprop": "author"})
            authors = author_element.text.strip() if author_element else "Unknown"

            # Extract abstract
            abstract = "Abstract not found"
            abstract_elements = [
                soup.find("div", class_="uscb-text-image-text"),
                soup.find("div", class_="cmp-text"),
            ]

            for abstract_element in abstract_elements:
                if abstract_element:
                    abstract = abstract_element.get_text(strip=True)
                    break

            # If abstract is still missing, use first paragraph with enough text
            if abstract == "Abstract not found":
                for paragraph in soup.find_all("p"):
                    text = paragraph.get_text(strip=True)
                    if len(text) > 50:
                        abstract = text
                        break

            return title_text, file_links, date_published, authors, abstract, None  # Success
        except requests.RequestException as e:
            print(f"⚠️ Attempt {attempt + 1}/{retries} failed for {url}: {e}")
            time.sleep(2)

    return "Title Not Found", [], "Unknown", "Unknown", "Abstract not found", "Failed after retries"

def download_file(url, retries=RETRY_ATTEMPTS):
    """Downloads a file and saves it with retry logic."""
    for attempt in range(retries):
        try:
            response = requests.get(url, stream=True, timeout=5)
            response.raise_for_status()
            parsed_url = urlparse(url)
            filename = re.sub(r'[<>:"/\\|?*]', "_", os.path.basename(parsed_url.path))
            file_path = os.path.join(DOWNLOAD_DIR, filename)

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

            return file_path, None  # Success
        except requests.RequestException as e:
            print(f"⚠️ Attempt {attempt + 1}/{retries} failed for {url}: {e}")
            time.sleep(2)

    return None, f"Failed after {retries} attempts"


# =============================================================================
#                     MAIN SCRAPING LOGIC WITH RETRIES
# =============================================================================

papers = []
url = "https://www.census.gov/library/working-papers.html"
driver.get(url)
page_count = 1
crawl_delay = 4

while True:
    print(f"📄 Scraping Page {page_count}...")

    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "uscb-default-x-column-title")))
    except:
        print("⚠️ Timeout waiting for page content. Exiting.")
        break

    titles = driver.find_elements(By.CLASS_NAME, "uscb-default-x-column-title")
    paper_data = []

    for i in range(len(titles)):
        try:
            title_element = driver.find_elements(By.CLASS_NAME, "uscb-default-x-column-title")[i]
            link_element = safe_find_element(driver, By.XPATH,
                                             f"(//a[contains(@href, '/library/working-papers/')])[{i + 1}]")

            if title_element and link_element:
                title_text = title_element.text.strip()
                link_url = link_element.get_attribute("href")

                if title_text and link_url and "series.html" not in link_url:
                    paper_data.append({"Title": title_text, "Link": link_url})

        except Exception as e:
            print(f"⚠️ Skipping entry due to error: {e}")
            continue

    # Process each paper page individually
    with ThreadPoolExecutor(max_workers=10) as executor:
        processed_papers = list(executor.map(get_page_data, [paper["Link"] for paper in paper_data]))

    # Update paper_data with extracted details
    for i, paper in enumerate(paper_data):
        title_text, file_links, date_published, authors, abstract, error = processed_papers[i]

        paper.update({
            "Title": title_text,  # Now getting title from the individual page
            "Download Links": "; ".join(file_links),
            "Date Published": date_published,
            "Authors": authors,
            "Abstract": abstract,
            "Downloaded Files": "",
            "Files Count": len(file_links),
            "Download Errors": error
        })

    papers.extend(paper_data)

    if page_count % SAVE_INTERVAL == 0:
        pd.DataFrame(papers).to_csv(TEMP_CSV, index=False)
        print(f"✅ Progress saved to {TEMP_CSV}")

    try:
        next_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "nextButton")))
        driver.execute_script("arguments[0].scrollIntoView();", next_button)
        time.sleep(1)
        next_button.click()
        time.sleep(crawl_delay)
        page_count += 1
    except:
        print("✅ No more pages to scrape.")
        break

driver.quit()

df_final = pd.DataFrame(papers)
df_final.to_csv(OUTPUT_CSV, index=False)
print(f"🎉 Scraping Complete! {len(papers)} papers saved to {OUTPUT_CSV}")
