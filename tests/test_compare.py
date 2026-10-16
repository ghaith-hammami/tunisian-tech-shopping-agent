import unittest

from shopping_agent.main import initial_state
from shopping_agent.nodes.compare import (
    assess_product,
    compare_node,
    gpu_score,
    phone_model_score,
)


def product(name="Laptop Example", brand="Example", **specs):
    return {
        "name": name,
        "brand": brand,
        "price_tnd": 4500.0,
        "category": "laptop",
        "specs": specs,
        "source": "tunisianet",
        "url": "https://example.test/product",
        "rating": 0.0,
        "reviews_count": 0,
    }


class CompareTests(unittest.TestCase):
    def test_rtx_5090_is_a_high_tier_gpu(self):
        self.assertEqual(gpu_score("NVIDIA RTX 5090"), 1.0)

    def test_phone_family_score_favors_camera_capable_series(self):
        self.assertGreater(
            phone_model_score("Samsung Galaxy A56"),
            phone_model_score("Samsung Galaxy A07"),
        )

    def test_missing_specs_are_unverified_not_failed(self):
        state = initial_state("gaming laptop")
        state["category"] = "laptop"
        state["required_specs"].update(
            {"min_ram_gb": 16, "min_storage_gb": 512}
        )
        gaps, unknown = assess_product(product(), state)
        self.assertEqual(gaps, [])
        self.assertIn("RAM not listed", unknown)
        self.assertIn("storage not listed", unknown)

    def test_explicit_brand_is_enforced(self):
        state = initial_state("Apple laptop")
        state["category"] = "laptop"
        state["required_specs"]["preferred_brands"] = ["Apple"]
        gaps, _ = assess_product(product(brand="Dell"), state)
        self.assertIn("brand is not Apple", gaps)

    def test_compare_keeps_verified_and_near_matches(self):
        state = initial_state("gaming laptop")
        state["category"] = "laptop"
        state["budget_max_tnd"] = 6000
        state["required_specs"].update(
            {
                "min_ram_gb": 16,
                "min_storage_gb": 512,
                "preferred_cpu_tier": "high",
                "requires_dedicated_gpu": True,
                "gpu_tier": "high",
                "min_gpu_vram_gb": 8,
            }
        )
        strong = product(
            name="Laptop RTX 5090",
            ram_gb=32,
            storage_gb=1000,
            cpu="Intel Core i9",
            gpu="RTX 5090",
            gpu_vram_gb=16,
        )
        state["products"] = [strong]
        compare_node(state)
        self.assertEqual(state["products"][0]["match_status"], "verified match")


if __name__ == "__main__":
    unittest.main()
