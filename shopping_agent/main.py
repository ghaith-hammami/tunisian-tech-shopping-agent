from .graph import app
from .state import AgentState, RequiredSpecs


def empty_required_specs() -> RequiredSpecs:
    return {
        "min_ram_gb": 0,
        "min_storage_gb": 0,
        "preferred_cpu_tier": None,
        "requires_dedicated_gpu": False,
        "gpu_tier": None,
        "min_gpu_vram_gb": 0,
        "camera_priority": None,
        "preferred_brands": [],
        "preferred_os": None,
    }


def initial_state(user_query: str) -> AgentState:
    return {
        "user_query": user_query,
        "category": None,
        "budget_min_tnd": None,
        "budget_max_tnd": None,
        "use_case": None,
        "required_specs": empty_required_specs(),
        "is_vague": False,
        "clarification_question": None,
        "sources_searched": [],
        "search_errors": [],
        "products": [],
        "next_action": "search",
        "decision_reason": "",
        "exact_matches_found": False,
        "final_recommendation": None,
        "reasoning_trace": [],
    }


def run_agent(user_query: str) -> AgentState:
    """Run the graph and return its final state for CLI or programmatic use."""
    query = user_query.strip()
    if not query:
        raise ValueError("The shopping query cannot be empty")
    return app.invoke(initial_state(query))


def main() -> None:
    print("Tunisian Tech Shopping Agent")
    print("Search live listings from Tunisianet, Mytek, and Spacenet.\n")
    query = input("What are you looking for? ").strip()
    if not query:
        print("Please enter a shopping request.")
        return

    try:
        run_agent(query)
    except (RuntimeError, ValueError) as exc:
        print(f"\nUnable to complete the search: {exc}")


if __name__ == "__main__":
    main()
