"""Unit tests for odoo.libs.ir_ui_view — no Odoo ORM dependency."""

import re
import unittest

from odoo.libs.ir_ui_view import (
    COMP_REGEX,
    MOVABLE_BRANDING,
    VIEW_MODIFIERS,
    ref_re,
)


class TestMovableBranding(unittest.TestCase):
    """Test MOVABLE_BRANDING constant."""

    def test_is_list(self):
        self.assertIsInstance(MOVABLE_BRANDING, list)

    def test_contains_model(self):
        self.assertIn("data-oe-model", MOVABLE_BRANDING)

    def test_contains_id(self):
        self.assertIn("data-oe-id", MOVABLE_BRANDING)

    def test_contains_field(self):
        self.assertIn("data-oe-field", MOVABLE_BRANDING)

    def test_contains_xpath(self):
        self.assertIn("data-oe-xpath", MOVABLE_BRANDING)

    def test_contains_source_id(self):
        self.assertIn("data-oe-source-id", MOVABLE_BRANDING)

    def test_length(self):
        self.assertEqual(len(MOVABLE_BRANDING), 5)


class TestViewModifiers(unittest.TestCase):
    """Test VIEW_MODIFIERS constant."""

    def test_is_tuple(self):
        self.assertIsInstance(VIEW_MODIFIERS, tuple)

    def test_contains_invisible(self):
        self.assertIn("invisible", VIEW_MODIFIERS)

    def test_contains_readonly(self):
        self.assertIn("readonly", VIEW_MODIFIERS)

    def test_contains_required(self):
        self.assertIn("required", VIEW_MODIFIERS)

    def test_contains_column_invisible(self):
        self.assertIn("column_invisible", VIEW_MODIFIERS)

    def test_length(self):
        self.assertEqual(len(VIEW_MODIFIERS), 4)


class TestCompRegex(unittest.TestCase):
    """Test COMP_REGEX pattern."""

    def test_matches_standalone(self):
        self.assertRegex("__comp__", COMP_REGEX)

    def test_matches_in_expression(self):
        self.assertRegex("x + __comp__.foo", COMP_REGEX)

    def test_no_match_in_word(self):
        """Should not match __comp__ embedded in a larger word."""
        self.assertIsNone(re.search(COMP_REGEX, "my__comp__var"))


class TestRefRe(unittest.TestCase):
    """Test ref_re compiled regex."""

    def test_is_compiled_pattern(self):
        self.assertIsInstance(ref_re, re.Pattern)

    def test_matches_single_quoted(self):
        text = "'form_view_ref': 'module.view_id'"
        match = ref_re.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group("view_type"), "form_view_ref")
        self.assertEqual(match.group("view_id"), "module.view_id")

    def test_matches_double_quoted(self):
        text = '"tree_view_ref": "module.tree_view"'
        match = ref_re.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group("view_type"), "tree_view_ref")
        self.assertEqual(match.group("view_id"), "module.tree_view")

    def test_matches_with_spaces(self):
        text = "'kanban_view_ref' : 'module.kanban_view'"
        match = ref_re.search(text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group("view_type"), "kanban_view_ref")

    def test_no_match_without_view_ref(self):
        text = "'name': 'some_value'"
        match = ref_re.search(text)
        self.assertIsNone(match)


if __name__ == "__main__":
    unittest.main()
