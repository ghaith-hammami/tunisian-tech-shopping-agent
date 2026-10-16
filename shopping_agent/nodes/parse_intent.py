import math
from typing import Any

from ..llm import call_json
from ..state import AgentState, Category, RequiredSpecs


SYSTEM_PROMPT = """
You extract shopping requirements for a Tunisian technology shopping agent.
Supported categories are laptop, pc, and phone. Infer practical minimum hardware
requirements from the stated use case. Preserve explicit brand and operating-system
preferences. A budget is money only when the user describes it as a price or uses a
currency; hardware model numbers such as RTX 5090 are not budgets.

Return one JSON object with these keys:
{
  "category": "laptop" | "pc" | "phone" | null,
  "budget_min_tnd": number | null,
  "budget_max_tnd": number | null,
  "use_case": string | null,
  "required_specs": {
    "min_ram_gb": number,
    "min_storage_gb": number,
    "preferred_cpu_tier": "entry" | "mid" | "high" | null,
    "requires_dedicated_gpu": boolean,
    "gpu_tier": "entry" | "mid" | "high" | null,
    "min_gpu_vram_gb": number,
    "camera_priority": "low" | "medium" | "high" | null,
    "preferred_brands": [string],
    "preferred_os": string | null
  }
}

Do not add commentary or infer a brand the user did not request.
"""

CATEGORIES = {"laptop", "pc", "phone"}
TIERS = {"entry", "mid", "high"}
CAMERA_PRIORITIES = {"low", "medium", "high"}


def _optional_choice(value: Any, choices: set[str]) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if normalized in choices else None


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _nonnegative_int(value: Any) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, number)


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _brands(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        brand = item.strip()
        if brand and brand.casefold() not in {name.casefold() for name in result}:
            result.append(brand)
    return result


def normalize_intent(raw: dict[str, Any]) -> tuple[
    Category | None,
    float | None,
    float | None,
    str | None,
    RequiredSpecs,
]:
    category = _optional_choice(raw.get("category"), CATEGORIES)
    budget_min = _positive_float(raw.get("budget_min_tnd"))
    budget_max = _positive_float(raw.get("budget_max_tnd"))
    if budget_min is not None and budget_max is not None and budget_min > budget_max:
        budget_min, budget_max = budget_max, budget_min

    spec_data = raw.get("required_specs")
    if not isinstance(spec_data, dict):
        spec_data = {}

    specs: RequiredSpecs = {
        "min_ram_gb": _nonnegative_int(spec_data.get("min_ram_gb")),
        "min_storage_gb": _nonnegative_int(spec_data.get("min_storage_gb")),
        "preferred_cpu_tier": _optional_choice(
            spec_data.get("preferred_cpu_tier"), TIERS
        ),
        "requires_dedicated_gpu": spec_data.get("requires_dedicated_gpu") is True,
        "gpu_tier": _optional_choice(spec_data.get("gpu_tier"), TIERS),
        "min_gpu_vram_gb": _nonnegative_int(spec_data.get("min_gpu_vram_gb")),
        "camera_priority": _optional_choice(
            spec_data.get("camera_priority"), CAMERA_PRIORITIES
        ),
        "preferred_brands": _brands(spec_data.get("preferred_brands")),
        "preferred_os": _optional_text(spec_data.get("preferred_os")),
    }
    return (
        category,  # type: ignore[return-value]
        budget_min,
        budget_max,
        _optional_text(raw.get("use_case")),
        specs,
    )


def parse_intent_node(state: AgentState) -> AgentState:
    result = call_json(SYSTEM_PROMPT, {"user_query": state["user_query"]})
    category, budget_min, budget_max, use_case, specs = normalize_intent(result)

    state["category"] = category
    state["budget_min_tnd"] = budget_min
    state["budget_max_tnd"] = budget_max
    state["use_case"] = use_case
    state["required_specs"] = specs

    state["is_vague"] = category is None or (use_case is None and budget_max is None)
    if category is None:
        question = "Are you looking for a laptop, desktop PC, or phone?"
    elif use_case is None and budget_max is None:
        question = "What will you mainly use it for, or what is your maximum budget?"
    else:
        question = None
    state["clarification_question"] = question

    summary = f"category={category}, use_case={use_case}, budget_max={budget_max}"
    state["reasoning_trace"].append(f"[intent] {summary}")
    print(f"[intent] {summary}")
    return state

