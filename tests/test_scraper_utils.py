import unittest

from shopping_agent.tools.scraper_utils import clean_price, extract_specs


class ScraperUtilityTests(unittest.TestCase):
    def test_tunisian_price_format(self):
        self.assertEqual(clean_price("1 299,000 DT"), 1299.0)

    def test_english_terabyte_storage(self):
        specs = extract_specs("Laptop 8GB RAM 1TB SSD")
        self.assertEqual(specs["ram_gb"], 8)
        self.assertEqual(specs["storage_gb"], 1000)

    def test_unlabelled_phone_memory_pair(self):
        specs = extract_specs("Samsung Galaxy A07 / 8 Go / 64 Go / Violet")
        self.assertEqual(specs["ram_gb"], 8)
        self.assertEqual(specs["storage_gb"], 64)


if __name__ == "__main__":
    unittest.main()
