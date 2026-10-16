import re

from ..state import AgentState, Product
from ..tools.scraper_utils import is_accessory, normalize_text


CPU_SCORES = (
    ("ultra 9", 1.00),
    ("ryzen ai 9", 1.00),
    ("ryzen 9", 0.96),
    ("core i9", 0.96),
    (" i9", 0.96),
    ("apple m5", 1.00),
    ("apple m4", 0.97),
    ("apple m3", 0.92),
    ("ultra 7", 0.88),
    ("ryzen ai 7", 0.90),
    ("ryzen 7", 0.84),
    ("core i7", 0.84),
    (" i7", 0.84),
    ("ultra 5", 0.72),
    ("ryzen ai 5", 0.74),
    ("ryzen 5", 0.68),
    ("core i5", 0.68),
    (" i5", 0.68),
    ("ryzen 3", 0.36),
    ("core i3", 0.36),
    (" i3", 0.36),
    ("n100", 0.18),
    ("n95", 0.16),
    ("celeron", 0.10),
)

GPU_SCORES = (
    ("rtx 5090", 1.00),
    ("rtx 5080", 0.98),
    ("rtx 5070 ti", 0.95),
    ("rtx 5070", 0.92),
    ("rtx 5060", 0.86),
    ("rtx 5050", 0.76),
    ("rtx 4090", 0.98),
    ("rtx 4080", 0.95),
    ("rtx 4070", 0.89),
    ("rtx 4060", 0.80),
    ("rtx 4050", 0.70),
    ("rtx 3070", 0.78),
    ("rtx 3060", 0.69),
    ("rtx 3050 ti", 0.58),
    ("rtx 3050", 0.52),
    ("gtx 1660", 0.46),
    ("gtx 1650", 0.40),
    ("radeon rx 7", 0.84),
    ("radeon rx 6", 0.70),
    ("intel arc", 0.50),
    (" mx", 0.28),
)

CPU_THRESHOLDS = {"entry": 0.30, "mid": 0.62, "high": 0.80}
GPU_THRESHOLDS = {"entry": 0.38, "mid": 0.68, "high": 0.84}
INTEGRATED_GPU_TERMS = ("intel uhd", "intel iris", "radeon graphics", "integrated")


def _spec_int(product: Product, key: str) -> int | None:
    value = product.get("specs", {}).get(key)
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _spec_text(product: Product, key: str) -> str:
    return str(product.get("specs", {}).get(key) or "").strip().lower()


def cpu_score(text: str) -> float | None:
    if not text:
        return None
    padded = f" {text.lower()}"
    for pattern, score in CPU_SCORES:
        if pattern in padded:
            return score
    return None


def gpu_score(text: str) -> float | None:
    if not text:
        return None
    padded = f" {text.lower()}"
    for pattern, score in GPU_SCORES:
        if pattern in padded:
            return score
    if any(term in padded for term in INTEGRATED_GPU_TERMS):
        return 0.12
    return None


def phone_model_score(name: str) -> float:
    """Estimate product-family position without maintaining a list of model years."""
    normalized = normalize_text(name)
    if re.search(r"\bgalaxy [sz]\d", normalized):
        return 1.0
    galaxy_a = re.search(r"\bgalaxy a(\d)", normalized)
    if galaxy_a:
        family = int(galaxy_a.group(1))
        return {0: 0.2, 1: 0.4, 2: 0.5, 3: 0.65, 4: 0.7}.get(family, 0.82)
    if any(term in normalized for term in ("iphone", "pixel", "xiaomi 1", "honor magic")):
        return 0.9
    if any(term in normalized for term in ("redmi note", "poco x", "reno")):
        return 0.6
    if any(term in normalized for term in ("redmi", "itel", "feature phone")):
        return 0.25
    return 0.45


def _brand_matches(product: Product, preferred_brands: list[str]) -> bool:
    product_text = f"{product['brand']} {product['name']}".casefold()
    return any(re.search(rf"\b{re.escape(brand.casefold())}\b", product_text) for brand in preferred_brands)


def assess_product(product: Product, state: AgentState) -> tuple[list[str], list[str]]:
    specs = state["required_specs"]
    gaps: list[str] = []
    unknown: list[str] = []

    if product["price_tnd"] <= 0:
        gaps.append("invalid price")
    elif state["budget_max_tnd"] and product["price_tnd"] > state["budget_max_tnd"]:
        gaps.append(f"over budget by {product['price_tnd'] - state['budget_max_tnd']:.0f} TND")

    brands = specs["preferred_brands"]
    if brands and not _brand_matches(product, brands):
        gaps.append(f"brand is not {', '.join(brands)}")

    preferred_os = (specs["preferred_os"] or "").casefold()
    name = product["name"].casefold()
    if preferred_os in {"ios", "iphone os"} and "iphone" not in name and product["brand"].casefold() != "apple":
        gaps.append("does not match the requested iOS platform")
    elif preferred_os == "android" and ("iphone" in name or product["brand"].casefold() == "apple"):
        gaps.append("does not match the requested Android platform")
    elif preferred_os in {"macos", "mac os"} and product["brand"].casefold() != "apple":
        gaps.append("does not match the requested macOS platform")

    checks = (
        ("ram_gb", specs["min_ram_gb"], "RAM"),
        ("storage_gb", specs["min_storage_gb"], "storage"),
        ("gpu_vram_gb", specs["min_gpu_vram_gb"], "GPU VRAM"),
    )
    for key, minimum, label in checks:
        if not minimum:
            continue
        actual = _spec_int(product, key)
        if actual is None:
            unknown.append(f"{label} not listed")
        elif actual < minimum:
            gaps.append(f"{label} is {actual}GB; needs at least {minimum}GB")

    cpu_tier = specs["preferred_cpu_tier"]
    if cpu_tier:
        score = cpu_score(_spec_text(product, "cpu"))
        if score is None:
            unknown.append("CPU tier not verified")
        elif score < CPU_THRESHOLDS[cpu_tier]:
            gaps.append(f"CPU is below the requested {cpu_tier} tier")

    gpu_tier = specs["gpu_tier"]
    requires_gpu = specs["requires_dedicated_gpu"]
    if requires_gpu or gpu_tier:
        text = _spec_text(product, "gpu")
        score = gpu_score(text)
        if score is None:
            unknown.append("dedicated GPU not verified")
        elif requires_gpu and any(term in text for term in INTEGRATED_GPU_TERMS):
            gaps.append("no dedicated GPU")
        elif score < GPU_THRESHOLDS[gpu_tier or "entry"]:
            gaps.append(f"GPU is below the requested {gpu_tier or 'entry'} tier")

    if specs["camera_priority"] == "high" and _spec_int(product, "camera_mp") is None:
        unknown.append("camera quality not verified")

    return gaps, unknown


def score_product(product: Product, state: AgentState, gaps: list[str], unknown: list[str]) -> float:
    score = 78.0 - (22.0 * len(gaps)) - (6.0 * len(unknown))
    ram = _spec_int(product, "ram_gb") or 0
    storage = _spec_int(product, "storage_gb") or 0
    score += min(5.0, ram / 8.0)
    score += min(5.0, storage / 256.0)
    score += 7.0 * (cpu_score(_spec_text(product, "cpu")) or 0.0)
    score += 7.0 * (gpu_score(_spec_text(product, "gpu")) or 0.0)

    if state["category"] == "phone":
        phone_weight = 18.0 if state["required_specs"]["camera_priority"] == "high" else 7.0
        score += phone_weight * phone_model_score(product["name"])

    budget = state["budget_max_tnd"]
    if budget and 0 < product["price_tnd"] <= budget:
        score += 4.0 * (1.0 - product["price_tnd"] / budget)

    rating = product.get("rating", 0.0)
    if rating > 0:
        score += min(4.0, rating / 5.0 * 4.0)
    return round(max(0.0, min(100.0, score)), 1)


def _model_key(product: Product) -> str:
    normalized = normalize_text(product["name"])
    colors = (
        "black", "blanc", "bleu", "blue", "gold", "gris", "green", "noir",
        "orange", "pink", "rose", "rouge", "silver", "vert", "violet", "white",
    )
    for color in colors:
        normalized = re.sub(rf"\b{color}\b", "", normalized)
    return re.sub(r"\W+", " ", normalized).strip()


def compare_node(state: AgentState) -> AgentState:
    ranked: list[Product] = []
    seen: set[tuple[str, str]] = set()
    for product in state["products"]:
        if is_accessory(product["name"]):
            continue
        key = (product["source"], product["url"])
        if key in seen:
            continue
        seen.add(key)

        candidate = product.copy()
        gaps, unknown = assess_product(candidate, state)
        candidate["requirement_gaps"] = gaps
        candidate["unverified_requirements"] = unknown
        if not gaps and not unknown:
            candidate["match_status"] = "verified match"
        elif not gaps:
            candidate["match_status"] = "compatible; some details unverified"
        else:
            candidate["match_status"] = "near match"
        candidate["score"] = score_product(candidate, state, gaps, unknown)
        ranked.append(candidate)

    ranked.sort(key=lambda item: (-item["score"], item["price_tnd"]))
    diverse: list[Product] = []
    model_keys: set[str] = set()
    for product in ranked:
        model_key = _model_key(product)
        if model_key in model_keys:
            continue
        model_keys.add(model_key)
        diverse.append(product)
    state["products"] = diverse[:6]
    state["exact_matches_found"] = any(
        not item.get("requirement_gaps") and not item.get("unverified_requirements")
        for item in ranked
    )
    message = f"[compare] Ranked {len(ranked)} candidates."
    state["reasoning_trace"].append(message)
    print(message)
    return state
