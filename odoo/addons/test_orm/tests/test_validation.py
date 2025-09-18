"""Characterization tests for ORM validation functions.

These tests lock down the current behavior of validation.py so that
refactoring (Phase 2: code quality) doesn't accidentally change semantics.
"""

from odoo.exceptions import AccessError, ValidationError
from odoo.orm.validation import (
    check_method_name,
    check_object_name,
    check_pg_name,
    raise_on_invalid_object_name,
)
from odoo.tests.common import TransactionCase


class TestCheckObjectName(TransactionCase):
    """Test model name validation — returns bool (not exception)."""

    def test_valid_dotted_name(self):
        self.assertTrue(check_object_name("res.partner"))

    def test_valid_underscored_name(self):
        self.assertTrue(check_object_name("my_module.my_model"))

    def test_valid_with_numbers(self):
        self.assertTrue(check_object_name("l10n_mx.tax_rate"))

    def test_rejects_uppercase(self):
        self.assertFalse(check_object_name("Res.Partner"))

    def test_rejects_spaces(self):
        self.assertFalse(check_object_name("res partner"))

    def test_rejects_hyphens(self):
        self.assertFalse(check_object_name("res-partner"))

    def test_rejects_empty(self):
        self.assertFalse(check_object_name(""))


class TestRaiseOnInvalidObjectName(TransactionCase):
    """Test the exception-raising wrapper."""

    def test_valid_name_no_error(self):
        # Should not raise
        raise_on_invalid_object_name("res.partner")

    def test_invalid_name_raises(self):
        with self.assertRaises(ValueError):
            raise_on_invalid_object_name("Invalid Name!")


class TestCheckPgName(TransactionCase):
    """Test PostgreSQL identifier validation — raises ValidationError."""

    def test_valid_simple(self):
        # Should not raise
        check_pg_name("my_table")

    def test_valid_with_dollar(self):
        check_pg_name("my_table$1")

    def test_rejects_too_long(self):
        with self.assertRaises(ValidationError):
            check_pg_name("a" * 64)

    def test_accepts_63_chars(self):
        check_pg_name("a" * 63)

    def test_rejects_starting_with_number(self):
        with self.assertRaises(ValidationError):
            check_pg_name("1invalid")

    def test_rejects_special_chars(self):
        with self.assertRaises(ValidationError):
            check_pg_name("my-table")


class TestCheckMethodName(TransactionCase):
    """Test RPC method name validation — raises AccessError for private methods."""

    def test_public_method_allowed(self):
        # Should not raise
        check_method_name("read")

    def test_private_method_blocked(self):
        with self.assertRaises(AccessError):
            check_method_name("_private_method")

    def test_dunder_method_blocked(self):
        with self.assertRaises(AccessError):
            check_method_name("__dunder__")

    def test_init_blocked(self):
        """The 'init' method is explicitly blocked for RPC."""
        with self.assertRaises(AccessError):
            check_method_name("init")

    def test_public_with_numbers(self):
        check_method_name("action_confirm_2")
