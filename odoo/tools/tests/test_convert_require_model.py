import ast
import inspect
import unittest

from odoo.tools import convert
from odoo.tools.convert import _check_model_name


class TestRequireModel(unittest.TestCase):
    def test_a_missing_model_is_refused(self):
        for value in (None, ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as caught:
                    _check_model_name(value)
                self.assertIn('model="..."', str(caught.exception))

    def test_a_model_passes_through(self):
        self.assertEqual(_check_model_name("res.partner"), "res.partner")

    def test_it_raises_rather_than_asserts(self):
        tree = ast.parse(inspect.getsource(convert))
        function = next(
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "_check_model_name"
        )
        self.assertFalse(
            [n for n in ast.walk(function) if isinstance(n, ast.Assert)],
            "data-file validation must not be an assert",
        )
        self.assertTrue([n for n in ast.walk(function) if isinstance(n, ast.Raise)])

    def test_the_search_validates_before_building_the_context(self):
        source = inspect.getsource(convert)
        tree = ast.parse(source)
        checked = 0
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            calls = [
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            ]
            if "_check_model_name" not in calls or "_prepare_eval_context" not in calls:
                continue
            checked += 1
            self.assertLess(
                calls.index("_check_model_name"),
                calls.index("_prepare_eval_context"),
                f"{node.name} builds the eval context before validating the model",
            )
        self.assertEqual(checked, 1, "expected the one <search> evaluator")


if __name__ == "__main__":
    unittest.main()
