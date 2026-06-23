import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import tempfile

from database.db import init_db, get_all_jobs, insert_jobs
from scraper.scraper import scrape_naukri_jobs
from agent.resume_parser import extract_resume_text
from agent.graph import build_graph

st.set_page_config(page_title="Job Application Agent", layout="wide")
init_db()
from database.db import seed_from_json_if_empty
seed_from_json_if_empty()

st.title("🤖 Autonomous Job Application Agent")
st.caption("LangGraph + Gemini-powered agent that scrapes, analyzes, and decides on job applications")


# SIDEBAR — CONTROLS
# ============================================================
with st.sidebar:
    st.header("⚙️ Controls")

    #  Step 1: Scrape 
    st.subheader("1️⃣ Scrape Jobs")

    IS_DEPLOYED = os.getenv("IS_DEPLOYED", "false").lower() == "true"

    if IS_DEPLOYED:
        st.info("🖥️ Live scraping requires a real browser and runs locally only (due to Naukri's anti-bot protection). The dashboard below shows jobs already scraped and analyzed. You can still upload your own resume and run the agent on these jobs!")
    else:
        search_query = st.text_input("Job search term", placeholder="e.g. AI ML Engineer fresher")
        max_jobs = st.slider("Max jobs to scrape", 5, 50, 5)

    if st.button("🔍 Scrape Jobs", use_container_width=True):
        if not search_query.strip():
            st.error("Please enter a search term.")
        else:
            with st.spinner(f"Scraping Naukri for '{search_query}'... a browser window will open."):
                scraped = scrape_naukri_jobs(search_query, max_jobs=max_jobs)
                insert_jobs(scraped)
            st.success(f"Scraped and saved {len(scraped)} jobs!")
            st.rerun()

    st.divider()

    # Step 2: Run Agent
    st.subheader("2️⃣ Run Agent")
    resume_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])

    if st.button("🚀 Run Agent on Pending Jobs", use_container_width=True):
        if resume_file is None:
            st.error("Please upload your resume PDF first.")
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(resume_file.read())
                tmp_path = tmp.name

            resume_text = extract_resume_text(tmp_path)

            initial_state = {
                "resume_text": resume_text,
                "candidate_skills": [],
                "jobs": [],
                "current_index": 0,
                "total_jobs": 0,
                "is_done": False,
            }

            app = build_graph()

            progress_bar = st.empty()
            log_container = st.container()

            final_state = None
            for step_output in app.stream(initial_state, {"recursion_limit": 200}):
                node_name = list(step_output.keys())[0]
                node_state = step_output[node_name]

                if node_state.get("total_jobs", 0) > 0:
                    pct = min(node_state["current_index"] / node_state["total_jobs"], 1.0)
                    progress_bar.progress(pct, text=f"Processing job {node_state['current_index']} of {node_state['total_jobs']}")

                if node_name == "analyze_job" and node_state.get("jobs"):
                    idx = node_state["current_index"]
                    if idx < len(node_state["jobs"]):
                        job = node_state["jobs"][idx]
                        if job.get("decision"):
                            with log_container:
                                emoji = "✅" if job["decision"] == "apply" else "⏭️"
                                st.write(
                                    f"{emoji} **{job['job_title']}** @ {job['company_name']} "
                                    f"— Score: {job['match_score']} — {job['decision'].upper()}"
                                )

                final_state = node_state

            st.success("Agent run complete!")
            st.rerun()


# MAIN DASHBOARD

jobs = get_all_jobs()

if not jobs:
    st.info("👈 Use the sidebar to scrape jobs and run the agent.")
    st.stop()

df = pd.DataFrame(jobs)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Jobs Scraped", len(df))
col2.metric("Applied", len(df[df["application_status"] == "applied"]))
col3.metric("Skipped", len(df[df["application_status"] == "skipped"]))
col4.metric("Pending", len(df[df["application_status"] == "pending"]))

st.divider()

chart_col, _ = st.columns([1, 2])
with chart_col:
    st.subheader("Application Status Breakdown")
    status_counts = df["application_status"].value_counts()
    st.bar_chart(status_counts)

st.divider()

status_filter = st.multiselect(
    "Filter by status",
    options=["applied", "skipped", "pending"],
    default=["applied", "skipped", "pending"],
)

filtered_df = df[df["application_status"].isin(status_filter)]
filtered_df = filtered_df.sort_values(by="match_score", ascending=False, na_position="last")

for _, job in filtered_df.iterrows():
    status_emoji = {"applied": "✅", "skipped": "⏭️", "pending": "⏳"}.get(job["application_status"], "❓")
    score_display = job['match_score'] if pd.notna(job['match_score']) else 'N/A'

    with st.expander(f"{status_emoji} **{job['job_title']}** @ {job['company_name']}  —  Score: {score_display}"):
        col_a, col_b = st.columns([2, 1])

        with col_a:
            st.markdown(f"**Experience Required:** {job['experience_required']}")
            st.markdown(f"**Status:** `{job['application_status']}`")
            if pd.notna(job["match_reasoning"]):
                st.markdown(f"**AI Reasoning:** {job['match_reasoning']}")
            st.markdown(f"**Job Description:** {job['job_description'][:300]}...")

        with col_b:
            if job["job_url"]:
                st.link_button("View Job Posting", job["job_url"])
            if pd.notna(job["match_score"]):
                st.metric("Match Score", f"{int(job['match_score'])}/100")