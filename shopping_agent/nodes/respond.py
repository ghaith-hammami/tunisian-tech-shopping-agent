from ..state import AgentState, Product


def _product_lines(product: Product, number: int | None = None) -> list[str]:
    prefix = f"{number}. " if number is not None else ""
    lines = [
        f"{prefix}{product['name']}",
        f"   {product['price_tnd']:.3f} TND | {product['source'].title()} | score {product['score']}/100",
        f"   Status: {product['match_status']}",
        f"   Link: {product['url']}",
    ]
    if product.get("requirement_gaps"):
        lines.append(f"   Gaps: {'; '.join(product['requirement_gaps'])}")
    if product.get("unverified_requirements"):
        lines.append(
            f"   Verify before buying: {'; '.join(product['unverified_requirements'])}"
        )
    return lines


def respond_node(state: AgentState) -> AgentState:
    lines = ["\n" + "=" * 64, "SHOPPING AGENT RESULT", "=" * 64]
    if not state["products"]:
        lines.append("No relevant products were found in the available store listings.")
    else:
        top_label = (
            "Closest available option:"
            if state["products"][0].get("requirement_gaps")
            else "Top recommendation:"
        )
        lines.extend([f"\n{top_label}", *_product_lines(state["products"][0])])
        if len(state["products"]) > 1:
            lines.append("\nAlternatives:")
            for index, product in enumerate(state["products"][1:], start=2):
                lines.extend(_product_lines(product, index))

    if state["search_errors"]:
        lines.append("\nStores that could not be searched:")
        lines.extend(f"- {error}" for error in state["search_errors"])

    lines.append("\nAgent trace:")
    lines.extend(f"- {event}" for event in state["reasoning_trace"])
    output = "\n".join(lines)
    state["final_recommendation"] = output
    print(output)
    return state
