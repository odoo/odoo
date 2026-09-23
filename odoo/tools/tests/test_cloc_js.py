import unittest

from odoo.tools.cloc import Cloc


def _code(source):
    return Cloc().parse_js(source)[0]


class TestJavaScriptLexing(unittest.TestCase):
    def test_a_quote_inside_a_template_literal_opens_no_string(self):
        source = (
            "static template = xml`<div>Don't panic</div>`;\n"
            "// comment one\n"
            "/* block\n   comment */\n"
            "const b = 'x';\n"
        )
        self.assertEqual(_code(source), 2)

    def test_a_multiline_template_counts_its_lines(self):
        self.assertEqual(_code("const a = `\n  one\n  two\n`;\n// c\n"), 4)

    def test_a_template_nested_in_a_substitution(self):
        source = "const a = `x ${c ? `y'` : \"z\"} w`;\n// comment\nconst q = 'it';\n"
        self.assertEqual(_code(source), 2)

    def test_braces_inside_a_substitution_do_not_end_it(self):
        self.assertEqual(_code("const u = `${ {a: 1}.a }'`;\n// c\nconst z = 1;\n"), 2)

    def test_a_quote_inside_a_regex_literal_opens_no_string(self):
        for source in (
            "const re = /[\"']/;\n// one\n// two\nconst b = 1;\n",
            "function f(s) {\n    return /[\"']/.test(s);\n}\n// c\n// d\n",
            'const re = /"/g;\n// one\nconst s = "a";\n// two\nconst t = 1;\n',
        ):
            with self.subTest(source=source):
                self.assertEqual(_code(source), source.count("\n") - 2)

    def test_division_is_not_a_regex(self):
        self.assertEqual(_code("const a = b / 2; // half\n// c\nd = (e) / f / g;\n"), 2)

    def test_slashes_inside_strings_are_not_comments(self):
        self.assertEqual(_code("const u = 'http://x';\nconst v = `https://${h}`;\n"), 2)

    def test_an_unterminated_quote_stops_at_its_line(self):
        self.assertEqual(_code("const a = 'oops;\n// comment\nconst b = 1;\n"), 2)


if __name__ == "__main__":
    unittest.main()
