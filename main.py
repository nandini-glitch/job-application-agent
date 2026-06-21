from scraper.scraper import scrape_naukri_jobs
from database.db import init_db, insert_jobs
from agent.resume_parser import extract_resume_text
from agent.graph import build_graph


def run_scraping_pipeline(search_query: str, max_jobs: int = 40):
    """
    Scrapes jobs from Naukri and stores them in SQLite.
    """
    print(f"Starting scrape for: '{search_query}'")
    init_db()
    scraped_jobs = scrape_naukri_jobs(search_query, max_jobs=max_jobs)
    insert_jobs(scraped_jobs)


def run_agent_pipeline(resume_path: str):
    """
    Runs the full LangGraph agent: loads pending jobs from DB,
    analyzes each against the resume, and decides apply/skip.
    """
    print("Extracting resume...")
    resume_text = extract_resume_text(resume_path)

    initial_state = {
        "resume_text": resume_text,
        "candidate_skills": [],
        "jobs": [],
        "current_index": 0,
        "total_jobs": 0,
        "is_done": False,
    }

    app = build_graph()
    final_state = app.invoke(initial_state, {"recursion_limit": 200})

    print("\n=== AGENT RUN COMPLETE ===")
    print(f"Total jobs processed: {final_state['total_jobs']}")

    applied_count = sum(1 for job in final_state["jobs"] if job["decision"] == "apply")
    skipped_count = sum(1 for job in final_state["jobs"] if job["decision"] == "skip")

    print(f"Applied: {applied_count} | Skipped: {skipped_count}")


if __name__ == "__main__":
    choice = input("Type 'scrape' to scrape new jobs, or 'run' to run the agent on existing pending jobs: ")

    if choice.strip().lower() == "scrape":
        query = input("Enter job search term: ")
        run_scraping_pipeline(query, max_jobs=40)
    elif choice.strip().lower() == "run":
        resume_path = input("Enter path to your resume PDF: ")
        run_agent_pipeline(resume_path)
    else:
        print("Invalid choice.")