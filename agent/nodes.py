import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from agent.state import AgentState
from database.db import update_job_decision, update_application_status, get_pending_jobs

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.2,
)

#nodes
# this first node func is the entry point to the graph
def load_jobs_node(state: AgentState) -> AgentState:
    """
    Entry point of the graph. Loads pending jobs from SQLite
    into state['jobs'], capped at a safe batch size to respect
    free-tier API rate limits, and sets up loop-tracking fields.
    """
    MAX_JOBS_PER_RUN = 15  # stays safely under the 20/day free-tier quota

    pending_jobs = get_pending_jobs()[:MAX_JOBS_PER_RUN]

    jobs = []
    for row in pending_jobs:
        jobs.append({
            "job_id": row["job_id"],
            "job_url": row["job_url"],
            "job_title": row["job_title"],
            "company_name": row["company_name"],
            "job_description": row["job_description"],
            "experience_required": row["experience_required"],
            "required_skills": [],
            "match_score": None,
            "match_reasoning": None,
            "decision": None,
            "application_status": "pending",
            "error_message": None,
            "timestamp": row["timestamp"],
        })

    state["jobs"] = jobs
    state["total_jobs"] = len(jobs)
    state["current_index"] = 0
    state["is_done"] = len(jobs) == 0

    print(f"Loaded {len(jobs)} pending jobs from database (capped at {MAX_JOBS_PER_RUN}/run).")

    return state

def analyze_job_node(state: AgentState) -> AgentState:
    """
    Takes the current job, compares it against the resume using Gemini,
    and fills in required_skills, match_score, match_reasoning, decision.
    """

    current_job = state["jobs"][state["current_index"]]
    resume_text = state["resume_text"]

    prompt = f"""
You are an AI recruiting assistant helping a candidate evaluate job fit.

CANDIDATE RESUME:
{resume_text}

JOB TITLE: {current_job['job_title']}
COMPANY: {current_job['company_name']}
EXPERIENCE REQUIRED: {current_job.get('experience_required', 'Not specified')}
JOB DESCRIPTION:
{current_job['job_description']}

Analyze the fit between this candidate and this job. Respond ONLY in valid JSON
with this exact structure, no markdown formatting, no backticks:

{{
  "required_skills": ["skill1", "skill2", "skill3"],
  "match_score": <number between 0 and 100>,
  "match_reasoning": "<2-3 sentence explanation of the score>",
  "decision": "<apply or skip>"
}}

Decision rule: "apply" if match_score >= 60, otherwise "skip".
"""

    response = llm.invoke(prompt)
    raw_text = response.content.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`").replace("json", "", 1).strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"Failed to parse Gemini response for job: {current_job['job_title']}")
        print(f"Raw response: {raw_text}")
        result = {
            "required_skills": [],
            "match_score": 0,
            "match_reasoning": "Failed to analyze due to parsing error.",
            "decision": "skip",
        }

    current_job["required_skills"] = result.get("required_skills", [])
    current_job["match_score"] = result.get("match_score", 0)
    current_job["match_reasoning"] = result.get("match_reasoning", "")
    current_job["decision"] = result.get("decision", "skip")

    print(f"\n[{current_job['job_title']} @ {current_job['company_name']}]")
    print(f"  Score: {current_job['match_score']} | Decision: {current_job['decision']}")
    print(f"  Reasoning: {current_job['match_reasoning']}")

    update_job_decision(
        job_id=current_job["job_id"],
        match_score=current_job["match_score"],
        match_reasoning=current_job["match_reasoning"],
        decision=current_job["decision"],
    )

    state["jobs"][state["current_index"]] = current_job
    return state


def apply_node(state: AgentState) -> AgentState:
    """
    Handles jobs where the decision was 'apply'.
    For now, this just logs/marks the application as 'applied' in the DB
    (actual auto-filling via Playwright is a future enhancement).
    """
    current_job = state["jobs"][state["current_index"]]

    print(f"  → Applying to: {current_job['job_title']} @ {current_job['company_name']}")

    current_job["application_status"] = "applied"

    update_application_status(
        job_id=current_job["job_id"],
        status="applied",
    )

    state["jobs"][state["current_index"]] = current_job
    return state


def skip_node(state: AgentState) -> AgentState:
    """
    Handles jobs where the decision was 'skip'.
    Just logs and marks status — no application action taken.
    """
    current_job = state["jobs"][state["current_index"]]

    print(f"  → Skipping: {current_job['job_title']} @ {current_job['company_name']}")

    current_job["application_status"] = "skipped"

    update_application_status(
        job_id=current_job["job_id"],
        status="skipped",
    )

    state["jobs"][state["current_index"]] = current_job
    return state


def move_to_next_job_node(state: AgentState) -> AgentState:
    """
    Advances the loop pointer to the next job.
    Sets is_done = True when all jobs have been processed.
    """
    state["current_index"] += 1

    if state["current_index"] >= state["total_jobs"]:
        state["is_done"] = True
        print("\nAll jobs processed.")
    else:
        state["is_done"] = False

    return state

#routing functions-conditional edges

def route_after_analysis(state: AgentState) -> str:
    """
    Conditional edge function — decides whether to go to
    'apply_node' or 'skip_node' based on the LLM's decision.
    NOT a node — used by LangGraph to pick the next path.
    """
    current_job = state["jobs"][state["current_index"]]
    return "apply" if current_job["decision"] == "apply" else "skip"


def route_after_action(state: AgentState) -> str:
    """
    Conditional edge function — decides whether to loop back to
    analyze the next job, or end the graph if all jobs are done.
    """
    return "end" if state["is_done"] else "continue"