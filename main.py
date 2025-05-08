import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import csv
import time

visited = set()
OUTPUT_FILE = "scraped_data.csv"
DEFAULT_DELAY = 2  # Fallback delay if robots.txt doesn't specify one

# Prepare CSV output
with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["URL", "Selector", "Content"])

def check_robots_and_delay(url):
    """Return (is_allowed, crawl_delay) for the given URL"""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urljoin(base_url, "/robots.txt")

    try:
        response = requests.get(robots_url, timeout=10)
        print(f"[robots.txt] Raw Content:\n{response.text}")  # Print the raw robots.txt content

        # Manually parse the robots.txt
        is_allowed = True  # Assume allowed by default
        delay = DEFAULT_DELAY  # Assume default delay
        
        # Split the content by lines and check for directives
        lines = response.text.splitlines()
        for line in lines:
            line = line.strip()
            if line.lower().startswith('user-agent:'):
                user_agent = line.split(":")[1].strip()
                if user_agent == '*' or user_agent.lower() == '*':
                    # Check for Crawl-delay in the same section
                    for sub_line in lines[lines.index(line)+1:]:
                        sub_line = sub_line.strip()
                        if sub_line.lower().startswith('crawl-delay:'):
                            delay = int(sub_line.split(":")[1].strip())
                            print(f"[robots.txt] Found crawl-delay: {delay} seconds")
                            break
                        elif sub_line.startswith("User-agent:"):
                            # Stop if a new User-agent section is encountered
                            break
        
        return is_allowed, delay
    except Exception as e:
        print(f"[robots.txt] Failed to read from {robots_url}: {e}")
        return False, DEFAULT_DELAY

def get_subdomain_links(url, domain):
    """Extract links to subdomains of the given domain"""
    links = set()
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        print(f"[Fetch Error] {url}: {e}")
        return links

    for tag in soup.find_all("a", href=True):
        href = tag['href']
        full_url = urljoin(url, href)
        parsed = urlparse(full_url)

        if parsed.netloc.endswith(domain):
            links.add(full_url)

    return links

def scrape_data(url, selectors):
    """Extract and save content using provided selectors"""
    print(f"[Scraping] {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print(response.text)
        print(response.status_code)
    except Exception as e:
        print(f"[Request Error] {url}: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    with open(OUTPUT_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for selector in selectors:
            elements = soup.select(selector)
            for el in elements[:5]:  # Limit to 5 elements per selector
                text = el.get_text(strip=True)
                if text:
                    writer.writerow([url, selector, text])
                    print(f"  - ({selector}) {text}")

def crawl_site(base_url, selectors):
    """Main crawl logic for a single target site"""
    parsed = urlparse(base_url)
    domain = parsed.netloc
    to_visit = {base_url}

    while to_visit:
        current_url = to_visit.pop()
        if current_url in visited:
            continue
        visited.add(current_url)

        allowed, delay = check_robots_and_delay(current_url)
        if not allowed:
            print(f"[robots.txt] Blocked: {current_url}")
            continue

        scrape_data(current_url, selectors)
        new_links = get_subdomain_links(current_url, domain)
        to_visit.update(new_links - visited)

        print(f"[Delay] Waiting {delay}s...")
        time.sleep(delay)

# --- Configuration ---
targets = [
    {
        "url": "https://www.pokemons.dk",
        "selectors": ["strong", "a.link-box"]
    }
]

for target in targets:
    crawl_site(target["url"], target["selectors"])

