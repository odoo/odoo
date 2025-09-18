"""Unit tests for odoo.libs.ir_qweb — no Odoo ORM dependency."""

import unittest

from odoo.libs.ir_qweb import (
    TO_VARNAME_REGEXP,
    VARNAME_REGEXP,
    has_malicious_scheme,
    id_or_xmlid,
    indent_code,
    is_valid_varname,
    sanitize_to_varname,
)

# ── Variable name utilities ──────────────────────────────────────────────


class TestVarnameRegexp(unittest.TestCase):
    """Test VARNAME_REGEXP pattern."""

    def test_simple_name(self):
        self.assertIsNotNone(VARNAME_REGEXP.match("foo"))

    def test_underscore_prefix(self):
        self.assertIsNotNone(VARNAME_REGEXP.match("_bar"))

    def test_with_digits(self):
        self.assertIsNotNone(VARNAME_REGEXP.match("foo123"))

    def test_digit_prefix_invalid(self):
        self.assertIsNone(VARNAME_REGEXP.match("123foo"))

    def test_empty_invalid(self):
        self.assertIsNone(VARNAME_REGEXP.match(""))

    def test_space_invalid(self):
        self.assertIsNone(VARNAME_REGEXP.match("foo bar"))

    def test_dot_invalid(self):
        self.assertIsNone(VARNAME_REGEXP.match("foo.bar"))


class TestToVarnameRegexp(unittest.TestCase):
    """Test TO_VARNAME_REGEXP pattern."""

    def test_replace_dots(self):
        self.assertEqual(TO_VARNAME_REGEXP.sub("_", "a.b.c"), "a_b_c")

    def test_replace_spaces(self):
        self.assertEqual(TO_VARNAME_REGEXP.sub("_", "hello world"), "hello_world")

    def test_no_replacement(self):
        self.assertEqual(TO_VARNAME_REGEXP.sub("_", "valid_name"), "valid_name")

    def test_consecutive_invalid(self):
        self.assertEqual(TO_VARNAME_REGEXP.sub("_", "a..b"), "a_b")


class TestIsValidVarname(unittest.TestCase):
    """Test is_valid_varname helper."""

    def test_valid(self):
        self.assertTrue(is_valid_varname("my_var"))

    def test_invalid_dash(self):
        self.assertFalse(is_valid_varname("my-var"))

    def test_invalid_digit_start(self):
        self.assertFalse(is_valid_varname("9x"))


class TestSanitizeToVarname(unittest.TestCase):
    """Test sanitize_to_varname helper."""

    def test_replace_dots_and_spaces(self):
        self.assertEqual(sanitize_to_varname("res.partner form"), "res_partner_form")

    def test_already_clean(self):
        self.assertEqual(sanitize_to_varname("my_var_99"), "my_var_99")


class TestIndentCode(unittest.TestCase):
    """Test indent_code function."""

    def test_simple_indent(self):
        result = indent_code("x = 1", 1)
        self.assertEqual(result, "    x = 1")

    def test_level_zero(self):
        result = indent_code("x = 1", 0)
        self.assertEqual(result, "x = 1")

    def test_dedents_first(self):
        code = """
            if True:
                pass
        """
        result = indent_code(code, 1)
        lines = result.split("\n")
        self.assertEqual(lines[0], "    if True:")
        self.assertEqual(lines[1], "        pass")

    def test_strips_surrounding_whitespace(self):
        result = indent_code("  \n  x = 1  \n  ", 0)
        self.assertEqual(result, "x = 1")

    def test_multiline(self):
        code = "a = 1\nb = 2"
        result = indent_code(code, 2)
        lines = result.split("\n")
        self.assertEqual(lines[0], "        a = 1")
        self.assertEqual(lines[1], "        b = 2")


# ── Malicious URL detection ─────────────────────────────────────────────


class TestHasMaliciousScheme(unittest.TestCase):
    """Test has_malicious_scheme function."""

    def test_plain_javascript(self):
        self.assertTrue(has_malicious_scheme("javascript:alert(1)"))

    def test_javascript_case_insensitive(self):
        self.assertTrue(has_malicious_scheme("JAVASCRIPT:alert(1)"))

    def test_javascript_mixed_case(self):
        self.assertTrue(has_malicious_scheme("JavaScript:void(0)"))

    def test_safe_history_back(self):
        self.assertFalse(has_malicious_scheme("javascript:history.back()"))

    def test_safe_window_history_back(self):
        self.assertFalse(has_malicious_scheme("javascript:window.history.back()"))

    def test_safe_history_back_with_space(self):
        self.assertFalse(has_malicious_scheme("javascript: history.back()"))

    def test_normal_http_url(self):
        self.assertFalse(has_malicious_scheme("https://example.com"))

    def test_normal_relative_url(self):
        self.assertFalse(has_malicious_scheme("/page/about"))

    def test_empty_string(self):
        self.assertFalse(has_malicious_scheme(""))

    def test_javascript_prompt(self):
        self.assertTrue(has_malicious_scheme("javascript:prompt('xss')"))


# ── XML-ID reference parsing ────────────────────────────────────────────


class TestIdOrXmlid(unittest.TestCase):
    """Test id_or_xmlid pure function."""

    def test_integer_string(self):
        self.assertEqual(id_or_xmlid("42"), 42)

    def test_xmlid_string(self):
        self.assertEqual(id_or_xmlid("web.layout"), "web.layout")

    def test_zero(self):
        self.assertEqual(id_or_xmlid("0"), 0)

    def test_negative_id(self):
        self.assertEqual(id_or_xmlid("-1"), -1)

    def test_empty_string(self):
        self.assertEqual(id_or_xmlid(""), "")

    def test_none_returns_none(self):
        self.assertIsNone(id_or_xmlid(None))


if __name__ == "__main__":
    unittest.main()
