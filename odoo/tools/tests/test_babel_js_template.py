import io
import unittest
from typing import Any

from odoo.tools.babel_extractors.javascript_extractor import extract_javascript

_OPTS: Any = {"jsx": True, "template_string": True, "parse_template_string": True}


def _extract(src):
    return list(extract_javascript(io.BytesIO(src.encode()), {"_t": None}, [], _OPTS))


class TestTemplateStringExtraction(unittest.TestCase):
    def test_plain_term_in_template_expression(self):
        results = _extract("const a = `${ _t('hello') }`;")
        self.assertEqual([(r[1], r[2]) for r in results], [("_t", "hello")])

    def test_escaped_quote_does_not_drop_term(self):
        results = _extract(r"""const a = `${ _t('don\'t drop me') }`;""")
        self.assertEqual([r[2] for r in results], ["don't drop me"])

    def test_escaped_double_quote_in_double_quoted_string(self):
        results = _extract(r"""const a = `${ _t("a\"b") }`;""")
        self.assertEqual([r[2] for r in results], ['a"b'])

    def test_escaped_backslash_before_quote_still_closes(self):
        results = _extract(r"""const a = `${ _t("path\\") }`;""")
        self.assertEqual([r[2] for r in results], ["path\\"])

    def test_term_after_class_object_key(self):
        results = _extract('const b = { class: "fa", title: _t("Move down") };')
        self.assertEqual([r[2] for r in results], ["Move down"])

    def test_term_after_class_property_assignment(self):
        results = _extract('info.class = "x"; info.message = _t("Moved");')
        self.assertEqual([r[2] for r in results], ["Moved"])

    def test_generator_function_definition_opens_no_call(self):
        results = _extract('function* gen(a) { yield _t("Generated"); }')
        self.assertEqual([r[2] for r in results], ["Generated"])

    def test_term_in_template_after_return(self):
        results = _extract('function f() { return `${a} ${_t("Offline")}`; }')
        self.assertEqual([r[2] for r in results], ["Offline"])

    def test_term_in_template_tagged_by_non_keyword(self):
        results = _extract('const m = markup`<span>${_t("Share")}</span>`;')
        self.assertEqual([r[2] for r in results], ["Share"])

    def test_keyword_tagged_template_is_the_term(self):
        results = _extract("const m = _t`Tagged`;")
        self.assertEqual([(r[1], r[2]) for r in results], [("_t", "Tagged")])


if __name__ == "__main__":
    unittest.main()
