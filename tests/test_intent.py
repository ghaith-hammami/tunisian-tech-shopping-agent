import unittest

from shopping_agent.nodes.parse_intent import normalize_intent


class NormalizeIntentTests(unittest.TestCase):
    def test_invalid_model_values_are_safely_normalized(self):
        category, minimum, maximum, use_case, specs = normalize_intent(
            {
                "category": "television",
                "budget_min_tnd": -1,
                "budget_max_tnd": "not a number",
                "required_specs": {
                    "min_ram_gb": "sixteen",
                    "preferred_cpu_tier": "extreme",
                    "preferred_brands": "Apple",
                },
            }
        )

        self.assertIsNone(category)
        self.assertIsNone(minimum)
        self.assertIsNone(maximum)
        self.assertIsNone(use_case)
        self.assertEqual(specs["min_ram_gb"], 0)
        self.assertIsNone(specs["preferred_cpu_tier"])
        self.assertEqual(specs["preferred_brands"], [])

    def test_reversed_budget_range_is_corrected(self):
        _, minimum, maximum, _, _ = normalize_intent(
            {"budget_min_tnd": 3000, "budget_max_tnd": 2000}
        )
        self.assertEqual((minimum, maximum), (2000.0, 3000.0))


if __name__ == "__main__":
    unittest.main()

