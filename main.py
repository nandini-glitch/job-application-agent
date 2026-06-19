from scraper.scraper import scrape_naukri_jobs
from database.db import init_db, insert_jobs, get_pending_jobs


def run_scraping_pipeline(search_query: str, max_jobs: int = 40):
    """
    Full pipeline: scrape jobs from Naukri, then store them in SQLite.
    """
    print(f"Starting scrape for: '{search_query}'")

    # Step 1: Initialize DB (creates table if not exists)
    init_db()

    # Step 2: Scrape jobs
    scraped_jobs = scrape_naukri_jobs(search_query, max_jobs=max_jobs)

    # Step 3: Save to database
    insert_jobs(scraped_jobs)

    # Step 4: Confirm what's pending
    pending = get_pending_jobs()
    print(f"\nTotal pending jobs ready for processing: {len(pending)}")

    return pending


if __name__ == "__main__":
    query = input("Enter job search term: ")
    run_scraping_pipeline(query, max_jobs=40)