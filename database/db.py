import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
import json

def seed_from_json_if_empty(json_path: str = "seed_data.json"):
    """
    If the jobs table is empty (e.g., fresh container start on Render),
    populate it from a committed JSON snapshot so the deployed demo
    always has data to show.
    """
    existing = get_all_jobs()
    if existing:
        print(f"Database already has {len(existing)} jobs — skipping seed.")
        return

    if not os.path.exists(json_path):
        print(f"No seed file found at {json_path} — starting with empty database.")
        return

    with open(json_path, "r") as f:
        seed_jobs = json.load(f)

    conn = get_connection()
    cursor = conn.cursor()

    for job in seed_jobs:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (
                    job_id, job_url, job_title, company_name,
                    job_description, experience_required, location,
                    match_score, match_reasoning, decision,
                    application_status, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.get("job_id"), job.get("job_url"), job.get("job_title"),
                job.get("company_name"), job.get("job_description"),
                job.get("experience_required"), job.get("location"),
                job.get("match_score"), job.get("match_reasoning"), job.get("decision"),
                job.get("application_status", "pending"), job.get("timestamp"),
            ))
        except Exception as e:
            print(f"Error seeding job {job.get('job_title')}: {e}")

    conn.commit()
    conn.close()
    print(f"Seeded database with {len(seed_jobs)} jobs from {json_path}.")


DB_PATH = os.getenv("DB_PATH", "jobs.db")


def get_connection():
    """Creates and returns a new SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, like a dict
    return conn


def init_db():
    """
    Creates the jobs table if it doesn't already exist.
    Call this once when the app starts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            job_url TEXT,
            job_title TEXT,
            company_name TEXT,
            job_description TEXT,
            experience_required TEXT,
            location TEXT,
            required_skills TEXT,

            match_score REAL,
            match_reasoning TEXT,
            decision TEXT,

            application_status TEXT DEFAULT 'pending',
            error_message TEXT,

            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized — 'jobs' table ready.")


def insert_jobs(jobs: List[Dict]):
    """
    Inserts a batch of scraped jobs into the database.
    Skips duplicates (based on job_url) automatically.
    """
    conn = get_connection()
    cursor = conn.cursor()

    inserted_count = 0

    for job in jobs:
        # Use job_url as a simple unique ID generator
        job_url = job.get("job_url") or ""
        job_id = job_url.split("-")[-1] if job_url else str(hash(job.get("job_title", "") + job.get("company_name", "")))

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (
                    job_id, job_url, job_title, company_name,
                    job_description, experience_required, location,
                    application_status, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job.get("job_url", ""),
                job.get("job_title", ""),
                job.get("company_name", ""),
                job.get("job_description", ""),
                job.get("experience_required", ""),
                job.get("location", ""),
                "pending",
                datetime.now().isoformat(),
            ))

            if cursor.rowcount > 0:
                inserted_count += 1

        except Exception as e:
            print(f"Error inserting job {job.get('job_title')}: {e}")

    conn.commit()
    conn.close()
    print(f"Inserted {inserted_count} new jobs (duplicates skipped).")


def get_pending_jobs() -> List[Dict]:
    """Fetches all jobs that haven't been processed yet."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE application_status = 'pending'")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def update_job_decision(job_id: str, match_score: float, match_reasoning: str, decision: str):
    """Updates a job after the agent has analyzed and scored it."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET match_score = ?, match_reasoning = ?, decision = ?
        WHERE job_id = ?
    """, (match_score, match_reasoning, decision, job_id))

    conn.commit()
    conn.close()


def update_application_status(job_id: str, status: str, error_message: Optional[str] = None):
    """Updates the final outcome after attempting to apply (or skip)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET application_status = ?, error_message = ?
        WHERE job_id = ?
    """, (status, error_message, job_id))

    conn.commit()
    conn.close()


def get_all_jobs() -> List[Dict]:
    """Fetches all jobs — useful for displaying in the Streamlit dashboard."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# Quick test — run this file directly to initialize and test the DB
if __name__ == "__main__":
    init_db()

    # Test insert with dummy data
    sample_jobs = [
        {
            "job_url": "https://naukri.com/job-listings-test-123456",
            "job_title": "Test ML Engineer",
            "company_name": "TestCorp",
            "job_description": "This is a test job description.",
            "experience_required": "0-2 Yrs",
        }
    ]
    insert_jobs(sample_jobs)

    pending = get_pending_jobs()
    print(f"\nPending jobs in DB: {len(pending)}")
    for job in pending:
        print(job)