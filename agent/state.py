from typing import TypedDict, Optional, List
from typing_extensions import Literal


class Job(TypedDict):
    """Represents a single scraped job and everything learned about it."""

    # ---- Job Identity -unique tracking id from db for every job
    job_id: str 
    job_url: str
    job_title: str
    company_name: str
    location: str  

    # ---- Scraped Job Details ----
    job_description: str #JD scraped from the page
    required_skills: List[str] #for job extracted by LLM
    experience_required: Optional[str] 

    # ---- Agent Decision Making ----
    match_score: Optional[float] #0-100 score by LLM
    match_reasoning: Optional[str] #why this score
    decision: Optional[Literal["apply", "skip"]] #should you apply

    # ---- Application Outcome ----
    application_status: Literal["pending", "applied", "skipped", "failed"]
    error_message: Optional[str]

    # metadata
    timestamp: Optional[str] #when this job was processed


class AgentState(TypedDict):
    """
    The GLOBAL state that flows through the LangGraph.
    Holds the entire batch of jobs + a pointer to track progress through the loop.
    """

    # ---- Candidate Data (loaded once, shared across all jobs) ----
    resume_text: str
    candidate_skills: List[str]
    preferred_location: Optional[str]  

    # ---- Batch of Jobs ----
    jobs: List[Job]            # All scraped jobs from this run
    current_index: int          # Pointer: which job in `jobs` we're processing now

    # ---- Loop Control ----
    total_jobs: int             # len(jobs), set once after scraping
    is_done: bool                # True when current_index >= total_jobs