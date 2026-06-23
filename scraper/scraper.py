from playwright.sync_api import sync_playwright
import time
import random


def scrape_naukri_jobs(search_query: str, max_jobs: int = 40):
    """
    Scrapes job listings from Naukri.com for a given search query,
    looping through multiple pages until max_jobs is reached.

    NOTE: Runs in headed mode (visible browser) intentionally — Naukri's
    Akamai bot-protection blocks headless browsers with an "Access Denied"
    page, even with spoofed user-agents. A visible Chrome window will pop
    up during scraping; this is expected behavior.

    Args:
        search_query: The job role/keywords to search for (required, no default).
        max_jobs: Maximum number of jobs to scrape across all pages.

    Returns:
        A list of dictionaries, each representing one scraped job.
    """
    print(f"DEBUG: scrape_naukri_jobs called with query='{search_query}'", flush=True)

    if not search_query or not search_query.strip():
        raise ValueError("search_query cannot be empty — please provide a job title/keyword to search.")

    jobs = []
    slug = search_query.lower().strip().replace(" ", "-")

    print("DEBUG: Entering sync_playwright context", flush=True)
    with sync_playwright() as p:
        print("DEBUG: Playwright context started, launching browser...", flush=True)
        browser = p.chromium.launch(headless=False)
        print("DEBUG: Browser launched successfully", flush=True)

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        print("DEBUG: Browser context created", flush=True)

        page = context.new_page()
        print("DEBUG: New page created", flush=True)

        page_num = 1

        while len(jobs) < max_jobs:
            if page_num == 1:
                url = f"https://www.naukri.com/{slug}-jobs"
            else:
                url = f"https://www.naukri.com/{slug}-jobs-{page_num}"

            print(f"DEBUG: Navigating to page {page_num}: {url}", flush=True)
            page.goto(url, timeout=60000)
            print(f"DEBUG: page.goto() completed for page {page_num}", flush=True)

            try:
                page.wait_for_selector("div.cust-job-tuple", timeout=15000)
                print(f"DEBUG: Job cards selector found on page {page_num}", flush=True)
            except Exception as e:
                print(f"DEBUG: No more job cards found on page {page_num}. Stopping pagination. Error: {e}", flush=True)
                break

            time.sleep(random.uniform(1, 2))

            for _ in range(5):
                page.mouse.wheel(0, 2000)
                time.sleep(random.uniform(0.8, 1.5))

            job_cards = page.query_selector_all("div.cust-job-tuple")
            print(f"DEBUG: Found {len(job_cards)} job cards on page {page_num}", flush=True)

            if len(job_cards) == 0:
                break

            for card in job_cards:
                if len(jobs) >= max_jobs:
                    break
                try:
                    title_el = card.query_selector("a.title")
                    company_el = card.query_selector("a.comp-name")
                    exp_el = card.query_selector("span.expwdth")
                    desc_el = card.query_selector("span.job-desc")
                    location_el = card.query_selector("span.locWdth")

                    job = {
                        "job_title": title_el.inner_text().strip() if title_el else "N/A",
                        "job_url": title_el.get_attribute("href") if title_el else "",
                        "company_name": company_el.inner_text().strip() if company_el else "N/A",
                        "experience_required": exp_el.inner_text().strip() if exp_el else "N/A",
                        "job_description": desc_el.inner_text().strip() if desc_el else "",
                        "location": location_el.inner_text().strip() if location_el else "N/A",
                    }
                    jobs.append(job)

                except Exception as e:
                    print(f"DEBUG: Skipping a job card due to error: {e}", flush=True)
                    continue

            page_num += 1
            time.sleep(random.uniform(1, 2))

        print("DEBUG: Closing browser", flush=True)
        browser.close()

    print(f"DEBUG: Scraped {len(jobs)} jobs successfully across {page_num} page(s)", flush=True)
    return jobs


if __name__ == "__main__":
    query = input("Enter job search term (e.g. 'AI ML Engineer fresher'): ")
    results = scrape_naukri_jobs(query, max_jobs=40)
    for job in results:
        print(job)
        print("---")