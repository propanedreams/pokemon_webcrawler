import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import csv
import time

visited = set()
OUTPUT_FILE = "scraped_data.csv"
RATE_LIMIT_SECONDS = 2  # delay between requests

# Prepare CSV file
with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["URL", "Selector", "Content"])

def is_allowed(url):
    """Check robots.txt for scraping permission"""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urljoin(base_url, "/robots.txt")

    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
    except:
        print(f"Could not read robots.txt from {base_url}")
        return False

    return rp.can_fetch("*", url)

def get_subdomain_links(url, domain):
    """Extract subdomain links"""
    links = set()
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return links

    for tag in soup.find_all("a", href=True):
        href = tag['href']
        full_url = urljoin(url, href)
        parsed = urlparse(full_url)

        if parsed.netloc.endswith(domain):
            links.add(full_url)

    return links

def scrape_data(url, selectors):
    """Scrape page content by CSS selectors"""
    print(f"\nScraping: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    with open(OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for selector in selectors:
            elements = soup.select(selector)
            for el in elements[:5]:  # limit results per selector
                text = el.get_text(strip=True)
                if text:
                    writer.writerow([url, selector, text])
                    print(f" - ({selector}) {text}")

def crawl_site(base_url, selectors):
    parsed = urlparse(base_url)
    domain = parsed.netloc
    to_visit = {base_url}

    while to_visit:
        current_url = to_visit.pop()
        if current_url in visited:
            continue
        visited.add(current_url)

        if not is_allowed(current_url):
            print(f"Blocked by robots.txt: {current_url}")
            continue

        scrape_data(current_url, selectors)
        new_links = get_subdomain_links(current_url, domain)
        to_visit.update(new_links - visited)

        time.sleep(RATE_LIMIT_SECONDS)  # rate limit

# --- Configuration ---
targets = [
    {
        "url": "https://www.python.org",
        "selectors": ["h2", "a.button"]
    },
    {
        "url": "https://www.wikipedia.org",
        "selectors": ["strong", "a.link-box"]
    }
]

for target in targets:
    crawl_site(target["url"], target["selectors"])

