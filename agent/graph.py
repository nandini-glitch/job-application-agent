from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes import (
    load_jobs_node,
    analyze_job_node,
    apply_node,
    skip_node,
    move_to_next_job_node,
    route_after_analysis,
    route_after_action,
)


def build_graph():
    """
    Builds and compiles the LangGraph StateGraph for the job application agent.
    """
    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node("load_jobs", load_jobs_node)
    graph.add_node("analyze_job", analyze_job_node)
    graph.add_node("apply", apply_node)
    graph.add_node("skip", skip_node)
    graph.add_node("move_to_next", move_to_next_job_node)

    # Entry point
    graph.set_entry_point("load_jobs")

    # load_jobs → analyze_job (always, just one path)
    graph.add_edge("load_jobs", "analyze_job")

    # analyze_job → apply OR skip (conditional, based on Gemini's decision)
    graph.add_conditional_edges(
        "analyze_job",
        route_after_analysis,
        {
            "apply": "apply",
            "skip": "skip",
        }
    )

    # both apply and skip → move_to_next (always)
    graph.add_edge("apply", "move_to_next")
    graph.add_edge("skip", "move_to_next")

    # move_to_next → loop back to analyze_job OR end (conditional)
    graph.add_conditional_edges(
        "move_to_next",
        route_after_action,
        {
            "continue": "analyze_job",
            "end": END,
        }
    )

    return graph.compile()