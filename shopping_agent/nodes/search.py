from ..state import AgentState
from ..tools.stores import STORE_ORDER, search_store


def search_node(state: AgentState) -> AgentState:
    store = next(
        (name for name in STORE_ORDER if name not in state["sources_searched"]),
        None,
    )
    if store is None:
        state["reasoning_trace"].append("[search] No stores remain.")
        return state

    print(f"[search] Searching {store}...")
    try:
        products = search_store(
            store=store,
            category=state["category"],
            max_price=state["budget_max_tnd"],
            required_specs=state["required_specs"],
        )
    except Exception as exc:
        products = []
        state["search_errors"].append(f"{store}: {exc}")

    state["sources_searched"].append(store)
    state["products"].extend(products)
    message = f"[search] {store}: {len(products)} products, {len(state['products'])} total"
    state["reasoning_trace"].append(message)
    print(message)
    return state
