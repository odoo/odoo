import io
import unittest

from odoo.tools.babel_extractors.python_extractor import extract_python


def _terms(src):
    return [r[2] for r in extract_python(io.BytesIO(src.encode()), {"_": None}, [], {})]


class TestPythonExtractorCallName(unittest.TestCase):
    def test_call_is_extracted(self):
        self.assertEqual(_terms('x = _("A term")\n'), ["A term"])

    def test_lambda_parameter_is_not_a_call(self):
        self.assertEqual(_terms('f = lambda _: ("Not a term %s" % x)\n'), [])

    def test_tuple_target_is_not_a_call(self):
        src = 'for _, (a, b) in [(1, ("Not a term", 2))]:\n    pass\n'
        self.assertEqual(_terms(src), [])

    def test_parenthesis_on_next_statement_is_not_a_call(self):
        self.assertEqual(_terms('_ = 1\n("Not a term")\n'), [])

    def test_keyword_argument_is_not_a_call(self):
        self.assertEqual(_terms('x = dict(_=("Not a term"))\n'), [])


if __name__ == "__main__":
    unittest.main()
