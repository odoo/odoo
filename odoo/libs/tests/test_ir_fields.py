"""Unit tests for odoo.libs.ir_fields — no Odoo ORM dependency."""

import unittest

from odoo.libs.ir_fields import (
    REFERENCING_FIELDS,
    exclude_ref_fields,
    only_ref_fields,
)


class TestReferencingFields(unittest.TestCase):
    """Test REFERENCING_FIELDS constant."""

    def test_contains_id(self):
        self.assertIn("id", REFERENCING_FIELDS)

    def test_contains_dot_id(self):
        self.assertIn(".id", REFERENCING_FIELDS)

    def test_contains_none(self):
        self.assertIn(None, REFERENCING_FIELDS)

    def test_is_frozenset(self):
        self.assertIsInstance(REFERENCING_FIELDS, frozenset)

    def test_length(self):
        self.assertEqual(len(REFERENCING_FIELDS), 3)


class TestOnlyRefFields(unittest.TestCase):
    """Test only_ref_fields function."""

    def test_filters_to_refs(self):
        record = {"id": 42, "name": "Test", ".id": 99, "email": "x@y"}
        result = only_ref_fields(record)
        self.assertEqual(result, {"id": 42, ".id": 99})

    def test_with_none_key(self):
        record = {None: "something", "id": 1, "name": "Test"}
        result = only_ref_fields(record)
        self.assertEqual(result, {None: "something", "id": 1})

    def test_empty_dict(self):
        self.assertEqual(only_ref_fields({}), {})

    def test_no_ref_fields(self):
        record = {"name": "Test", "email": "test@test.com"}
        self.assertEqual(only_ref_fields(record), {})


class TestExcludeRefFields(unittest.TestCase):
    """Test exclude_ref_fields function."""

    def test_filters_out_refs(self):
        record = {"id": 42, "name": "Test", ".id": 99, "email": "x@y"}
        result = exclude_ref_fields(record)
        self.assertEqual(result, {"name": "Test", "email": "x@y"})

    def test_with_none_key(self):
        record = {None: "something", "name": "Test"}
        result = exclude_ref_fields(record)
        self.assertEqual(result, {"name": "Test"})

    def test_empty_dict(self):
        self.assertEqual(exclude_ref_fields({}), {})

    def test_only_ref_fields_returns_empty(self):
        record = {"id": 42, ".id": 99}
        self.assertEqual(exclude_ref_fields(record), {})


if __name__ == "__main__":
    unittest.main()
