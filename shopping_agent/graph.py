from langgraph.graph import END, StateGraph

from .nodes.clarify import clarify_node
from .nodes.compare import compare_node
from .nodes.evaluate_results import evaluate_results_node
from .nodes.parse_intent import parse_intent_node
from .nodes.respond import respond_node
from .nodes.search import search_node
from .state import AgentState


def route_after_intent(state: AgentState) -> str:
    return "clarify" if state["is_vague"] else "search"


def route_after_evaluation(state: AgentState) -> str:
    return state["next_action"]


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("parse_intent", parse_intent_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("search", search_node)
    graph.add_node("evaluate_results", evaluate_results_node)
    graph.add_node("compare", compare_node)
    graph.add_node("respond", respond_node)

    graph.set_entry_point("parse_intent")
    graph.add_conditional_edges(
        "parse_intent",
        route_after_intent,
        {"clarify": "clarify", "search": "search"},
    )
    graph.add_edge("clarify", "parse_intent")
    graph.add_edge("search", "evaluate_results")
    graph.add_conditional_edges(
        "evaluate_results",
        route_after_evaluation,
        {"search": "search", "compare": "compare"},
    )
    graph.add_edge("compare", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


app = build_graph()
