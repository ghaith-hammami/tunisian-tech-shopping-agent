from __future__ import annotations

import os
import re
import unicodedata
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..state import Category, Product


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
}


def env_int(name: str, default: int, minimum: int = 0, maximum: int = 100) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def env_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def _build_session() -> requests.Session:
    retries = env_int("SHOPPING_HTTP_RETRIES", 1, maximum=4)
    retry = Retry(
        total=retries,
        backoff_factor=0.35,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.headers.update(HEADERS)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


_SESSION = _build_session()


def fetch_soup(url: str) -> BeautifulSoup:
    timeout = (
        env_float("SHOPPING_HTTP_CONNECT_TIMEOUT", 4.0),
        env_float("SHOPPING_HTTP_READ_TIMEOUT", 8.0),
    )
    try:
        response = _SESSION.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"request failed: {exc}") from exc
    return BeautifulSoup(response.text, "html.parser")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _parse_price_token(token: str) -> float | None:
    compact = re.sub(r"\s+", "", token)
    if not compact or not re.search(r"\d", compact):
        return None

    separators = [index for index, char in enumerate(compact) if char in ",."]
    if not separators:
        digits = re.sub(r"\D", "", compact)
        return float(digits) if digits else None

    final_separator = separators[-1]
    left = re.sub(r"\D", "", compact[:final_separator])
    right = re.sub(r"\D", "", compact[final_separator + 1 :])
    if not left:
        return None

    # Tunisian stores commonly render 1299 TND as 1 299,000 or 1.299,000.
    if len(right) == 3:
        return float(left + right) if len(left) <= 2 and len(separators) == 1 else float(left)
    return float(f"{left}.{right}") if right else float(left)


def clean_price(text: str) -> float | None:
    if not text:
        return None
    currency_values = re.findall(
        r"(\d[\d\s.,]*?)\s*(?:TND|DT)\b", text.replace("\xa0", " "), re.IGNORECASE
    )
    values = currency_values or re.findall(r"\b\d[\d\s.,]*\b", text)
    prices = [_parse_price_token(value) for value in values]
    valid = [price for price in prices if price is not None and price > 0]
    return valid[-1] if valid else None


BRANDS = (
    "acer", "apple", "asus", "bmax", "chuwi", "dell", "gigabyte", "google",
    "honor", "hp", "huawei", "infinix", "itel", "lenovo", "msi", "nokia",
    "oneplus", "oppo", "poco", "realme", "redmi", "samsung", "tecno", "vivo",
    "xiaomi",
)


def guess_brand(name: str) -> str:
    normalized = normalize_text(name)
    if any(product_name in normalized for product_name in ("iphone", "macbook", "ipad")):
        return "Apple"
    for brand in BRANDS:
        if re.search(rf"\b{re.escape(brand)}\b", normalized):
            if brand in {"hp", "msi"}:
                return brand.upper()
            return "Apple" if brand == "apple" else brand.title()
    return "Unknown"


ACCESSORY_TERMS = (
    "adaptateur", "backpack", "cable", "casque", "chargeur", "clavier", "coque",
    "cooling pad", "ecouteur", "housse", "keyboard", "mouse", "sac a dos",
    "sacoche", "souris", "support pc", "verre trempe",
)


def is_accessory(name: str) -> bool:
    normalized = normalize_text(name)
    return any(term in normalized for term in ACCESSORY_TERMS)


def extract_specs(text: str) -> dict[str, object]:
    normalized = normalize_text(text)
    specs: dict[str, object] = {}

    gigabyte_values = [
        int(match.group(1))
        for match in re.finditer(r"\b(\d{1,4})\s*(?:go|gb)\b", normalized)
    ]
    explicit_ram = re.search(
        r"(?:ram|memoire)\s*:?[ ]*(\d{1,2})\s*(?:go|gb)|"
        r"(\d{1,2})\s*(?:go|gb)\s*(?:ram|ddr[345])",
        normalized,
    )
    if explicit_ram:
        specs["ram_gb"] = int(explicit_ram.group(1) or explicit_ram.group(2))
    elif len(gigabyte_values) >= 2 and gigabyte_values[0] <= 64:
        specs["ram_gb"] = gigabyte_values[0]

    storage_values = [value for value in gigabyte_values if value >= 128]
    if len(gigabyte_values) >= 2 and gigabyte_values[-1] >= 32:
        storage_values.append(gigabyte_values[-1])
    storage_values.extend(
        int(value) * 1000
        for value in re.findall(r"\b(\d+)\s*(?:to|tb)\b", normalized)
    )
    if storage_values:
        specs["storage_gb"] = max(storage_values)

    cpu_patterns = (
        r"intel core ultra [579](?:[-\w]*)?",
        r"intel core i[3579](?:[-\w]*)?",
        r"amd ryzen ai [579](?:[-\w+]*)?",
        r"amd ryzen [3579](?:[-\w]*)?",
        r"apple m[1-5](?: pro|max)?",
        r"intel n\d+",
        r"(?:celeron|pentium)(?:[-\w]*)?",
    )
    for pattern in cpu_patterns:
        match = re.search(pattern, normalized)
        if match:
            specs["cpu"] = match.group(0)
            break

    gpu_match = re.search(
        r"(?:rtx|gtx|mx)\s?\d{3,4}(?:\s?ti)?|radeon rx\s?\d{3,4}|intel arc|intel iris xe|intel uhd|radeon graphics",
        normalized,
    )
    if gpu_match:
        specs["gpu"] = gpu_match.group(0)

    vram_match = re.search(
        r"\b(\d{1,2})\s*(?:go|gb).{0,20}(?:gddr|vram|memoire dediee|dedicated)",
        normalized,
    )
    if vram_match:
        specs["gpu_vram_gb"] = int(vram_match.group(1))

    camera_match = re.search(r"\b(\d{2,3})\s*(?:mp|mpx)\b", normalized)
    if camera_match:
        specs["camera_mp"] = int(camera_match.group(1))
    return specs


def first_text(card: Tag, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        node = card.select_one(selector)
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return ""


def first_url(card: Tag, selectors: tuple[str, ...], base_url: str) -> str:
    for selector in selectors:
        node = card.select_one(selector)
        if node and node.get("href"):
            return urljoin(base_url, str(node["href"]))
    return ""


def build_product(
    name: str,
    price_tnd: float,
    url: str,
    source: str,
    category: Category,
    description: str,
) -> Product:
    return {
        "name": re.sub(r"\s+", " ", name).strip(),
        "brand": guess_brand(name),
        "price_tnd": price_tnd,
        "category": category,
        "specs": extract_specs(f"{name} {description}"),
        "source": source,
        "url": url,
        "rating": 0.0,
        "reviews_count": 0,
    }
