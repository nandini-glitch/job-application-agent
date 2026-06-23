# 🤖 Autonomous Job Application Agent

An AI agent that scrapes job listings, evaluates fit against a candidate's resume using an LLM, and decides whether to apply — built with **LangGraph**, **Gemini**, **Playwright**, and **Streamlit**.

---

## Overview

This project automates the early stages of a job search: finding relevant listings, reading each job description, comparing it against a resume, and making an apply/skip decision with reasoning — all orchestrated as a stateful graph rather than a single linear script.

The agent is designed around a **scrape-once, loop-and-decide** architecture:
Scrape jobs (Naukri) → Store in SQLite → Loop: analyze → decide → apply/skip → next job
---

## Features

- **Web scraping** — Pulls live job listings from Naukri.com with pagination support
- **LLM-powered analysis** — Gemini compares each job description against the candidate's resume and produces a match score, reasoning, and a decision
- **Stateful agent graph** — Built with LangGraph's `StateGraph`, using conditional edges to route between apply/skip and to loop until all jobs are processed
- **Persistent storage** — SQLite tracks every job's status, score, and reasoning, so the agent can resume exactly where it left off across runs
- **Interactive dashboard** — A Streamlit UI to trigger scraping, run the agent, and review live, node-by-node progress and results

---

## Tech Stack

| Layer | Tool |
|---|---|
| Agent orchestration | LangGraph |
| LLM | Google Gemini (`gemini-2.5-flash`) |
| Web scraping | Playwright |
| Database | SQLite |
| Resume parsing | pypdf |
| UI | Streamlit |
| Observability | LangSmith |
| Package management | uv |

---

## Architecture

**State** (`agent/state.py`) — A single `AgentState` TypedDict holds the entire batch of scraped jobs plus a loop pointer (`current_index`), rather than passing one job through the graph at a time. This lets LangGraph manage the iteration internally via conditional edges instead of an external Python loop.

**Nodes** (`agent/nodes.py`):
- `load_jobs_node` — pulls pending jobs from SQLite into state
- `analyze_job_node` — sends the job description + resume to Gemini, parses a structured JSON response (skills, score, reasoning, decision)
- `apply_node` / `skip_node` — record the outcome
- `move_to_next_job_node` — advances the loop pointer
- `route_after_analysis` / `route_after_action` — conditional-edge functions that decide which path the graph takes next

**Graph** (`agent/graph.py`) — Wires the nodes together with `add_conditional_edges`, forming a loop that runs until every job in the batch has been processed.

---

## Notable Engineering Challenges

**Naukri's bot protection.** Headless Playwright was blocked by Akamai's bot-detection layer with an explicit "Access Denied" response — even with a spoofed user-agent. Diagnosed by capturing a screenshot mid-failure to rule out a selector bug, then fixed by switching to headed (visible) browser mode with randomized human-like delays between actions.

**LLM rate limits.** Gemini's free tier caps daily requests well below what's needed to process a full batch of scraped jobs in one sitting. Rather than letting the agent fail outright, the database-backed state means progress is checkpointed after every job — a run can be safely stopped and resumed later, picking up exactly where it left off.

---

## Running Locally

```bash
# Install dependencies
uv sync
playwright install chromium

# Set up environment variables in .env
GOOGLE_API_KEY=your_key_here
LANGSMITH_API_KEY=your_key_here
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=job-application-agent

# Run the dashboard
uv run streamlit run ui/app.py
```

From the dashboard:
1. Enter a job search term and click **Scrape Jobs**
2. Upload a resume PDF and click **Run Agent** to analyze pending jobs

> **Note:** The scraper intentionally runs Playwright in headed (visible) mode rather than headless. Naukri's Akamai bot-protection blocks headless browsers outright, so a real Chrome window will open during scraping — this is expected behavior, not a bug.

---

## Project Structure
job-application-agent/

├── agent/
│   ├── state.py            # AgentState + Job type definitions
│   ├── nodes.py             # Graph nodes and routing functions
│   ├── graph.py             # LangGraph StateGraph wiring
│   └── resume_parser.py     # PDF text extraction
├── scraper/
│   └── scraper.py           # Naukri scraper (Playwright)
├── database/
│   └── db.py                # SQLite CRUD operations
├── ui/
│   └── app.py               # Streamlit dashboard
└── main.py                  # CLI entry point
---

## Future Enhancements

- Real auto-fill application submission via Playwright (currently logs the decision rather than submitting)
- Support for additional job boards beyond Naukri
- Resume-to-job skill gap analysis with improvement suggestions
