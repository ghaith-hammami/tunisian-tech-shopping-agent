import unittest
from unittest.mock import patch

from shopping_agent.main import initial_state
from shopping_agent.nodes.evaluate_results import evaluate_results_node
from shopping_agent.nodes.search import search_node


class GraphNodeTests(unittest.TestCase):
    @patch("shopping_agent.nodes.search.search_store", return_value=[])
    def test_search_node_searches_exactly_one_store(self, mocked_search):
        state = initial_state("laptop for programming under 2000 TND")
        state["category"] = "laptop"
        state["budget_max_tnd"] = 2000

        search_node(state)

        mocked_search.assert_called_once()
        self.assertEqual(state["sources_searched"], ["tunisianet"])
        self.assertIn("required_specs", mocked_search.call_args.kwargs)

    def test_empty_results_continue_until_stores_are_exhausted(self):
        state = initial_state("laptop")
        state["category"] = "laptop"
        state["sources_searched"] = ["tunisianet"]
        evaluate_results_node(state)
        self.assertEqual(state["next_action"], "search")

        state["sources_searched"] = ["tunisianet", "mytek", "spacenet"]
        evaluate_results_node(state)
        self.assertEqual(state["next_action"], "compare")


if __name__ == "__main__":
    unittest.main()
