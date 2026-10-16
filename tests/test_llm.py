import unittest
from unittest.mock import patch

from shopping_agent.llm import call_json


class RateLimitError(Exception):
    status_code = 429


class FailingModels:
    def generate_content(self, **kwargs):
        raise RateLimitError("quota exhausted")


class FailingClient:
    models = FailingModels()


class LlmTests(unittest.TestCase):
    @patch("shopping_agent.llm._get_client", return_value=FailingClient())
    def test_rate_limit_has_a_clear_error(self, _):
        with self.assertRaisesRegex(RuntimeError, "rate limit reached"):
            call_json("Return JSON", {"value": 1})


if __name__ == "__main__":
    unittest.main()

