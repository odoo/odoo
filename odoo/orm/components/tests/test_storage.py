"""Pure-Python tests for DictBackend — no Odoo, no database required."""

import unittest

from odoo.orm.components.storage import DictBackend


class TestDictBackendInsert(unittest.TestCase):
    """Test insert operations."""

    def setUp(self):
        self.backend = DictBackend()

    def test_insert_single(self):
        ids = self.backend.insert_rows("partner", ["name"], [("Alice",)])
        self.assertEqual(len(ids), 1)
        self.assertEqual(ids[0], 1)

    def test_insert_multiple(self):
        ids = self.backend.insert_rows(
            "partner",
            ["name", "email"],
            [("Alice", "a@x.com"), ("Bob", "b@x.com")],
        )
        self.assertEqual(ids, [1, 2])

    def test_insert_auto_increment(self):
        ids1 = self.backend.insert_rows("partner", ["name"], [("Alice",)])
        ids2 = self.backend.insert_rows("partner", ["name"], [("Bob",)])
        self.assertEqual(ids1, [1])
        self.assertEqual(ids2, [2])

    def test_insert_different_tables(self):
        ids1 = self.backend.insert_rows("partner", ["name"], [("Alice",)])
        ids2 = self.backend.insert_rows("product", ["name"], [("Widget",)])
        # separate sequences
        self.assertEqual(ids1, [1])
        self.assertEqual(ids2, [1])

    def test_insert_empty(self):
        ids = self.backend.insert_rows("partner", ["name"], [])
        self.assertEqual(ids, [])


class TestDictBackendFetch(unittest.TestCase):
    """Test fetch operations."""

    def setUp(self):
        self.backend = DictBackend()
        self.backend.insert_rows(
            "partner",
            ["name", "email"],
            [("Alice", "a@x.com"), ("Bob", "b@x.com")],
        )

    def test_fetch_all_columns(self):
        rows = self.backend.fetch_rows("partner", [1, 2], ["name", "email"])
        self.assertEqual(rows, [("Alice", "a@x.com"), ("Bob", "b@x.com")])

    def test_fetch_subset_columns(self):
        rows = self.backend.fetch_rows("partner", [1], ["name"])
        self.assertEqual(rows, [("Alice",)])

    def test_fetch_missing_id(self):
        rows = self.backend.fetch_rows("partner", [999], ["name"])
        self.assertEqual(rows, [])

    def test_fetch_mixed_ids(self):
        rows = self.backend.fetch_rows("partner", [1, 999], ["name"])
        self.assertEqual(rows, [("Alice",)])

    def test_fetch_missing_column(self):
        rows = self.backend.fetch_rows("partner", [1], ["nonexistent"])
        self.assertEqual(rows, [(None,)])

    def test_fetch_empty_table(self):
        rows = self.backend.fetch_rows("empty_table", [1], ["name"])
        self.assertEqual(rows, [])


class TestDictBackendUpdate(unittest.TestCase):
    """Test update operations."""

    def setUp(self):
        self.backend = DictBackend()
        self.backend.insert_rows("partner", ["name", "email"], [("Alice", "a@x.com")])

    def test_update_single_field(self):
        self.backend.update_rows("partner", [(1, {"name": "Alicia"})])
        rows = self.backend.fetch_rows("partner", [1], ["name", "email"])
        self.assertEqual(rows, [("Alicia", "a@x.com")])

    def test_update_multiple_fields(self):
        self.backend.update_rows(
            "partner", [(1, {"name": "Alicia", "email": "new@x.com"})]
        )
        rows = self.backend.fetch_rows("partner", [1], ["name", "email"])
        self.assertEqual(rows, [("Alicia", "new@x.com")])

    def test_update_nonexistent_id(self):
        # should not raise
        self.backend.update_rows("partner", [(999, {"name": "Ghost"})])

    def test_update_nonexistent_table(self):
        # should not raise
        self.backend.update_rows("nonexistent", [(1, {"name": "Ghost"})])


class TestDictBackendDelete(unittest.TestCase):
    """Test delete operations."""

    def setUp(self):
        self.backend = DictBackend()
        self.backend.insert_rows(
            "partner",
            ["name"],
            [("Alice",), ("Bob",)],
        )

    def test_delete_single(self):
        self.backend.delete_rows("partner", [1])
        self.assertEqual(self.backend.row_count("partner"), 1)
        rows = self.backend.fetch_rows("partner", [1], ["name"])
        self.assertEqual(rows, [])

    def test_delete_multiple(self):
        self.backend.delete_rows("partner", [1, 2])
        self.assertEqual(self.backend.row_count("partner"), 0)

    def test_delete_nonexistent(self):
        # should not raise
        self.backend.delete_rows("partner", [999])
        self.assertEqual(self.backend.row_count("partner"), 2)

    def test_delete_nonexistent_table(self):
        # should not raise
        self.backend.delete_rows("nonexistent", [1])


class TestDictBackendHelpers(unittest.TestCase):
    """Test helper methods."""

    def setUp(self):
        self.backend = DictBackend()

    def test_get_row(self):
        self.backend.insert_rows("partner", ["name"], [("Alice",)])
        row = self.backend.get_row("partner", 1)
        self.assertEqual(row, {"name": "Alice"})

    def test_get_row_missing(self):
        self.assertIsNone(self.backend.get_row("partner", 1))

    def test_table_ids(self):
        self.backend.insert_rows("partner", ["name"], [("Alice",), ("Bob",)])
        self.assertEqual(self.backend.table_ids("partner"), [1, 2])

    def test_table_ids_empty(self):
        self.assertEqual(self.backend.table_ids("partner"), [])

    def test_row_count(self):
        self.assertEqual(self.backend.row_count("partner"), 0)
        self.backend.insert_rows("partner", ["name"], [("Alice",)])
        self.assertEqual(self.backend.row_count("partner"), 1)

    def test_repr(self):
        self.backend.insert_rows("partner", ["name"], [("Alice",)])
        r = repr(self.backend)
        self.assertIn("tables=1", r)
        self.assertIn("rows=1", r)


if __name__ == "__main__":
    unittest.main()
