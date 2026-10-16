from ..state import AgentState


def clarify_node(state: AgentState) -> AgentState:
    question = state["clarification_question"] or "Could you clarify what you need?"
    print(f"\n{question}")

    answer = ""
    while not answer:
        answer = input("Your answer: ").strip()
        if not answer:
            print("Please provide a little more detail.")

    state["user_query"] = f"{state['user_query']} {answer}"
    state["reasoning_trace"].append("[clarify] Added the user's clarification.")
    return state

