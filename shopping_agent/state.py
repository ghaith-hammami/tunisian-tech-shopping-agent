from typing import Literal, NotRequired, TypedDict


Category = Literal["laptop", "pc", "phone"]
NextAction = Literal["search", "compare"]


class RequiredSpecs(TypedDict):
    min_ram_gb: int
    min_storage_gb: int
    preferred_cpu_tier: Literal["entry", "mid", "high"] | None
    requires_dedicated_gpu: bool
    gpu_tier: Literal["entry", "mid", "high"] | None
    min_gpu_vram_gb: int
    camera_priority: Literal["low", "medium", "high"] | None
    preferred_brands: list[str]
    preferred_os: str | None


class Product(TypedDict):
    name: str
    brand: str
    price_tnd: float
    category: Category
    specs: dict[str, object]
    source: str
    url: str
    rating: float
    reviews_count: int
    score: NotRequired[float]
    requirement_gaps: NotRequired[list[str]]
    unverified_requirements: NotRequired[list[str]]
    match_status: NotRequired[str]


class AgentState(TypedDict):
    user_query: str
    category: Category | None
    budget_min_tnd: float | None
    budget_max_tnd: float | None
    use_case: str | None
    required_specs: RequiredSpecs
    is_vague: bool
    clarification_question: str | None
    sources_searched: list[str]
    search_errors: list[str]
    products: list[Product]
    next_action: NextAction
    decision_reason: str
    exact_matches_found: bool
    final_recommendation: str | None
    reasoning_trace: list[str]
