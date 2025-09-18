"""Pure-Python tests for ComputeEngine — no Odoo, no database required.

Uses plain strings as mock "field" keys and integers as record IDs.
"""

import unittest

from odoo.orm.components.compute import ComputeEngine


class TestComputeScheduling(unittest.TestCase):
    """Test schedule / mark_done / pending queries."""

    def setUp(self):
        self.engine = ComputeEngine()

    def test_initially_empty(self):
        self.assertFalse(self.engine.has_pending())
        self.assertEqual(list(self.engine.pending_fields()), [])

    def test_schedule(self):
        self.engine.schedule("total", [1, 2, 3])
        self.assertTrue(self.engine.has_pending())
        self.assertTrue(self.engine.is_pending("total", 1))
        self.assertFalse(self.engine.is_pending("total", 99))

    def test_schedule_idempotent(self):
        self.engine.schedule("total", [1, 2])
        self.engine.schedule("total", [2, 3])
        ids = self.engine.pending_ids("total")
        self.assertEqual(set(ids), {1, 2, 3})

    def test_mark_done(self):
        self.engine.schedule("total", [1, 2, 3])
        self.engine.mark_done("total", [1, 2])
        self.assertFalse(self.engine.is_pending("total", 1))
        self.assertTrue(self.engine.is_pending("total", 3))

    def test_mark_done_removes_empty_field(self):
        self.engine.schedule("total", [1])
        self.engine.mark_done("total", [1])
        # field entry should be deleted
        self.assertFalse(self.engine.has_pending())
        self.assertNotIn("total", self.engine._pending)

    def test_mark_done_nonexistent(self):
        # should not raise
        self.engine.mark_done("total", [1, 2])

    def test_pending_fields(self):
        self.engine.schedule("total", [1])
        self.engine.schedule("tax", [2])
        fields = set(self.engine.pending_fields())
        self.assertEqual(fields, {"total", "tax"})

    def test_pending_ids_empty(self):
        ids = self.engine.pending_ids("nonexistent")
        self.assertEqual(len(ids), 0)

    def test_pending_real_fields(self):
        # Use 0 as a "falsy" NewId stand-in
        self.engine.schedule("total", [0])
        self.engine.schedule("tax", [1])
        real = self.engine.pending_real_fields()
        self.assertEqual(real, ["tax"])

    def test_pending_real_fields_mixed(self):
        self.engine.schedule("total", [0, 1])
        real = self.engine.pending_real_fields()
        # has at least one real (1), so included
        self.assertEqual(real, ["total"])

    def test_prune_empty(self):
        self.engine.schedule("total", [1])
        self.engine._pending["total"].clear()
        # entry still exists but is empty
        self.assertIn("total", self.engine._pending)
        self.engine.prune_empty()
        self.assertNotIn("total", self.engine._pending)

    def test_has_pending_field(self):
        self.assertFalse(self.engine.has_pending_field("total"))
        self.engine.schedule("total", [1])
        self.assertTrue(self.engine.has_pending_field("total"))
        self.assertFalse(self.engine.has_pending_field("tax"))

    def test_has_pending_field_empty_set(self):
        """has_pending_field returns True even if the set was auto-created and is empty."""
        self.engine.schedule("total", [1])
        self.engine.mark_done("total", [1])
        # mark_done deletes the entry when empty
        self.assertFalse(self.engine.has_pending_field("total"))

    def test_discard_field(self):
        self.engine.schedule("total", [1, 2])
        self.engine.schedule("tax", [3])
        self.engine.discard_field("total")
        self.assertFalse(self.engine.has_pending_field("total"))
        self.assertTrue(self.engine.has_pending_field("tax"))

    def test_discard_field_missing(self):
        # should not raise for a field that was never scheduled
        self.engine.discard_field("nonexistent")

    def test_clear(self):
        self.engine.schedule("total", [1, 2])
        self.engine.schedule("tax", [3])
        self.engine.clear()
        self.assertFalse(self.engine.has_pending())


class TestComputeProtection(unittest.TestCase):
    """Test field protection stack."""

    def setUp(self):
        self.engine = ComputeEngine()

    def test_initially_not_protected(self):
        self.assertFalse(self.engine.is_protected("total", 1))
        self.assertEqual(self.engine.protected_ids("total"), frozenset())

    def test_protect(self):
        self.engine.push_protection()
        self.engine.protect("total", frozenset([1, 2]))
        self.assertTrue(self.engine.is_protected("total", 1))
        self.assertFalse(self.engine.is_protected("total", 3))

    def test_nested_protection(self):
        self.engine.push_protection()
        self.engine.protect("total", frozenset([1]))
        # push another scope
        self.engine.push_protection()
        self.engine.protect("total", frozenset([2]))
        # both should be protected (search top to bottom)
        self.assertTrue(self.engine.is_protected("total", 1))
        self.assertTrue(self.engine.is_protected("total", 2))
        # pop inner scope
        self.engine.pop_protection()
        # id 2 no longer protected, id 1 still is
        self.assertTrue(self.engine.is_protected("total", 1))
        self.assertFalse(self.engine.is_protected("total", 2))

    def test_protect_merges_in_same_scope(self):
        self.engine.push_protection()
        self.engine.protect("total", frozenset([1]))
        self.engine.protect("total", frozenset([2]))
        self.assertTrue(self.engine.is_protected("total", 1))
        self.assertTrue(self.engine.is_protected("total", 2))

    def test_pop_returns_scope(self):
        self.engine.push_protection()
        self.engine.protect("total", frozenset([1]))
        scope = self.engine.pop_protection()
        self.assertIn("total", scope)

    def test_protected_ids(self):
        self.engine.push_protection()
        self.engine.protect("total", frozenset([1, 2]))
        ids = self.engine.protected_ids("total")
        self.assertEqual(ids, frozenset([1, 2]))


class TestComputeEngineRepr(unittest.TestCase):
    """Test repr."""

    def test_repr_empty(self):
        engine = ComputeEngine()
        r = repr(engine)
        self.assertIn("pending=0", r)
        self.assertIn("scopes=0", r)

    def test_repr_with_data(self):
        engine = ComputeEngine()
        engine.schedule("total", [1, 2])
        engine.push_protection()
        r = repr(engine)
        self.assertIn("pending=1f/2e", r)
        self.assertIn("scopes=1", r)


class TestComputeCustomFactory(unittest.TestCase):
    """Test with custom pending factory (OrderedSet-like)."""

    def test_custom_factory(self):
        class OrderedSet(set):
            pass

        engine = ComputeEngine(pending_factory=OrderedSet)
        engine.schedule("total", [1, 2])
        pending = engine._pending["total"]
        self.assertIsInstance(pending, OrderedSet)


if __name__ == "__main__":
    unittest.main()
