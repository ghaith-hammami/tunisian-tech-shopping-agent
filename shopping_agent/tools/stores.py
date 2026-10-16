from dataclasses import dataclass
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import Tag

from ..state import Category, Product, RequiredSpecs
from .scraper_utils import (
    build_product,
    clean_price,
    env_int,
    fetch_soup,
    first_text,
    first_url,
)


@dataclass(frozen=True)
class StoreConfig:
    base_url: str
    category_urls: dict[Category, str]
    search_url_template: str
    page_parameter: str
    card_selector: str
    name_selectors: tuple[str, ...]
    price_selectors: tuple[str, ...]
    link_selectors: tuple[str, ...]


STORE_ORDER = ("tunisianet", "mytek", "spacenet")

STORES = {
    "tunisianet": StoreConfig(
        base_url="https://www.tunisianet.com.tn",
        category_urls={
            "laptop": "https://www.tunisianet.com.tn/702-ordinateur-portable",
            "pc": "https://www.tunisianet.com.tn/701-ordinateur-de-bureau",
            "phone": "https://www.tunisianet.com.tn/596-smartphone-tunisie",
        },
        search_url_template="https://www.tunisianet.com.tn/recherche?controller=search&s={query}",
        page_parameter="page",
        card_selector="article.product-miniature, .js-product-miniature, .thumbnail-container",
        name_selectors=(".product-title", "a.product-name", "h2", "h3"),
        price_selectors=(".current-price .price", ".price", "span[class*='price']"),
        link_selectors=("a.product-thumbnail", "a.product-title", "a[href]"),
    ),
    "mytek": StoreConfig(
        base_url="https://www.mytek.tn",
        category_urls={
            "laptop": "https://www.mytek.tn/informatique/ordinateurs-portables.html",
            "pc": "https://www.mytek.tn/informatique/ordinateur-de-bureau.html",
            "phone": "https://www.mytek.tn/telephonie-tunisie/smartphone-mobile-tunisie.html",
        },
        search_url_template="https://www.mytek.tn/catalogsearch/result/?q={query}",
        page_parameter="p",
        card_selector="#seo-product-data [data-name][data-url], li.product-item, div.product-item",
        name_selectors=("a.product-item-link", ".product-item-link", "h2", "h3"),
        price_selectors=(".price-wrapper .price", ".price", "span[class*='price']"),
        link_selectors=("a.product-item-link", "a[href]"),
    ),
    "spacenet": StoreConfig(
        base_url="https://spacenet.tn",
        category_urls={
            "laptop": "https://spacenet.tn/18-ordinateur-portable",
            "pc": "https://spacenet.tn/73-ordinateur-bureau-tunisie",
            "phone": "https://spacenet.tn/13-smartphone-mobile-tunisie",
        },
        search_url_template="https://spacenet.tn/recherche?controller=search&s={query}",
        page_parameter="page",
        card_selector="article.product-miniature, .js-product-miniature, .thumbnail-container",
        name_selectors=(".product-title", "h2", "h3"),
        price_selectors=(".current-price .price", ".price", "span[class*='price']"),
        link_selectors=("a.product-thumbnail", "a.product-title", "a[href]"),
    ),
}


def _with_page(url: str, parameter: str, page: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[parameter] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _product_from_card(
    card: Tag,
    store: str,
    config: StoreConfig,
    category: Category,
) -> Product | None:
    name = str(card.get("data-name") or "").strip() or first_text(
        card, config.name_selectors
    )
    price_text = str(
        card.get("data-final-price") or card.get("data-price") or ""
    ).strip() or first_text(card, config.price_selectors)
    data_url = str(card.get("data-url") or "").strip()
    url = urljoin(config.base_url, data_url) if data_url else first_url(
        card, config.link_selectors, config.base_url
    )
    price = clean_price(price_text)
    if not name or price is None or not url:
        return None

    description = str(card.get("data-description") or "")
    if not description:
        description = card.get_text(" ", strip=True)
    return build_product(name, price, url, store, category, description)


def search_store(
    store: str,
    category: Category | None,
    max_price: float | None,
    required_specs: RequiredSpecs | None = None,
) -> list[Product]:
    if category is None:
        raise ValueError("A product category is required before searching")
    if store not in STORES:
        raise ValueError(f"Unknown store: {store}")

    config = STORES[store]
    max_pages = env_int("SHOPPING_MAX_PAGES_PER_STORE", 3, minimum=1, maximum=10)
    max_products = env_int(
        "SHOPPING_MAX_PRODUCTS_PER_STORE", 24, minimum=1, maximum=100
    )
    products: list[Product] = []
    seen_urls: set[str] = set()
    specs = required_specs or {}
    preferred_brands = [
        str(brand).casefold() for brand in specs.get("preferred_brands", [])
    ]
    requires_gpu = specs.get("requires_dedicated_gpu") is True
    search_terms = [*preferred_brands]
    if requires_gpu:
        search_terms.append("RTX")
    if search_terms:
        category_term = {"laptop": "laptop", "pc": "desktop pc", "phone": "smartphone"}[
            category
        ]
        query = quote_plus(" ".join([*search_terms, category_term]))
        listing_url = config.search_url_template.format(query=query)
    else:
        listing_url = config.category_urls[category]

    for page in range(1, max_pages + 1):
        soup = fetch_soup(_with_page(listing_url, config.page_parameter, page))
        cards = soup.select(config.card_selector)
        if not cards:
            break

        added = 0
        for card in cards:
            product = _product_from_card(card, store, config, category)
            if product is None or product["url"] in seen_urls:
                continue
            if max_price is not None and product["price_tnd"] > max_price:
                continue
            product_text = f"{product['brand']} {product['name']}".casefold()
            if preferred_brands and not any(
                brand in product_text for brand in preferred_brands
            ):
                continue
            if requires_gpu and not any(
                marker in str(product["specs"].get("gpu", "")).casefold()
                for marker in ("rtx", "gtx", "radeon rx", "intel arc", "mx")
            ):
                continue
            seen_urls.add(product["url"])
            products.append(product)
            added += 1
            if len(products) >= max_products:
                return products
        if added == 0:
            break

    return products
