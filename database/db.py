import sqlite3
from datetime import datetime
from typing import List, Dict, Optional


DB_PATH = "jobs.db"


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
        job_id = job.get("job_url", "").split("-")[-1] or str(hash(job.get("job_url", "")))

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (
                    job_id, job_url, job_title, company_name,
                    job_description, experience_required,
                    application_status, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job.get("job_url", ""),
                job.get("job_title", ""),
                job.get("company_name", ""),
                job.get("job_description", ""),
                job.get("experience_required", ""),
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