"""Pure-Python tests for FieldCache — no Odoo, no database required.

Uses plain strings as mock "field" keys to prove the cache is fully
decoupled from the ORM runtime.
"""

import unittest

from odoo.orm.components.cache import FieldCache


class TestFieldCacheData(unittest.TestCase):
    """Test basic data access: get, set, has, batch operations."""

    def setUp(self):
        self.cache = FieldCache()

    def test_set_and_get(self):
        self.cache.set_value("name", 1, "Alice")
        self.assertEqual(self.cache.get_value("name", 1), "Alice")

    def test_get_missing_raises(self):
        with self.assertRaises(KeyError):
            self.cache.get_value("name", 999)

    def test_get_missing_with_default(self):
        result = self.cache.get_value("name", 999, default=None)
        self.assertIsNone(result)

    def test_get_none_value_is_not_missing(self):
        self.cache.set_value("name", 1, None)
        self.assertIsNone(self.cache.get_value("name", 1))
        self.assertTrue(self.cache.has_value("name", 1))

    def test_has_value(self):
        self.assertFalse(self.cache.has_value("name", 1))
        self.cache.set_value("name", 1, "Alice")
        self.assertTrue(self.cache.has_value("name", 1))

    def test_has_value_wrong_field(self):
        self.cache.set_value("name", 1, "Alice")
        self.assertFalse(self.cache.has_value("email", 1))

    def test_get_field_data_creates_dict(self):
        d = self.cache.get_field_data("name")
        self.assertIsInstance(d, dict)
        self.assertEqual(len(d), 0)
        # mutating the returned dict is visible to the cache
        d[1] = "Bob"
        self.assertEqual(self.cache.get_value("name", 1), "Bob")

    def test_get_field_data_or_none(self):
        self.assertIsNone(self.cache.get_field_data_or_none("name"))
        self.cache.set_value("name", 1, "Alice")
        self.assertIsNotNone(self.cache.get_field_data_or_none("name"))

    def test_update_batch_singleton(self):
        self.cache.update_batch("state", (1,), "draft")
        self.assertEqual(self.cache.get_value("state", 1), "draft")

    def test_update_batch_multiple(self):
        self.cache.update_batch("state", (1, 2, 3), "confirmed")
        for id_ in (1, 2, 3):
            self.assertEqual(self.cache.get_value("state", id_), "confirmed")

    def test_update_batch_empty(self):
        # should not raise
        self.cache.update_batch("state", (), "draft")
        self.assertFalse(self.cache.has_value("state", 1))

    def test_insert_if_absent_no_overwrite(self):
        self.cache.set_value("name", 1, "Alice")
        self.cache.insert_if_absent("name", [1, 2], ["Bob", "Carol"])
        # id 1 keeps "Alice" (was already cached)
        self.assertEqual(self.cache.get_value("name", 1), "Alice")
        # id 2 gets "Carol" (was not cached)
        self.assertEqual(self.cache.get_value("name", 2), "Carol")

    def test_insert_if_absent_all_new(self):
        self.cache.insert_if_absent("name", [1, 2], ["Alice", "Bob"])
        self.assertEqual(self.cache.get_value("name", 1), "Alice")
        self.assertEqual(self.cache.get_value("name", 2), "Bob")

    def test_pop_value(self):
        self.cache.set_value("name", 1, "Alice")
        val = self.cache.pop_value("name", 1)
        self.assertEqual(val, "Alice")
        self.assertFalse(self.cache.has_value("name", 1))

    def test_pop_value_missing_raises(self):
        with self.assertRaises(KeyError):
            self.cache.pop_value("name", 999)

    def test_pop_value_missing_default(self):
        val = self.cache.pop_value("name", 999, default="fallback")
        self.assertEqual(val, "fallback")


class TestFieldCacheDirty(unittest.TestCase):
    """Test dirty tracking."""

    def setUp(self):
        self.cache = FieldCache()

    def test_initially_not_dirty(self):
        self.assertFalse(self.cache.is_any_dirty())
        self.assertIsNone(self.cache.get_dirty("name"))

    def test_mark_dirty(self):
        self.cache.mark_dirty("name", [1, 2])
        self.assertTrue(self.cache.is_any_dirty())
        self.assertEqual(self.cache.get_dirty("name"), {1, 2})

    def test_mark_dirty_idempotent(self):
        self.cache.mark_dirty("name", [1])
        self.cache.mark_dirty("name", [1])
        self.assertEqual(len(self.cache.get_dirty("name")), 1)

    def test_has_dirty_field(self):
        self.assertFalse(self.cache.has_dirty_field("name"))
        self.cache.mark_dirty("name", [1])
        self.assertTrue(self.cache.has_dirty_field("name"))
        self.assertFalse(self.cache.has_dirty_field("email"))

    def test_pop_dirty(self):
        self.cache.mark_dirty("name", [1, 2])
        ids = self.cache.pop_dirty("name")
        self.assertEqual(ids, {1, 2})
        # after pop, field is no longer dirty
        self.assertIsNone(self.cache.get_dirty("name"))
        self.assertFalse(self.cache.is_any_dirty())

    def test_pop_dirty_missing(self):
        self.assertIsNone(self.cache.pop_dirty("name"))

    def test_iter_dirty_fields(self):
        self.cache.mark_dirty("name", [1])
        self.cache.mark_dirty("email", [2, 3])
        fields = set(self.cache.iter_dirty_fields())
        self.assertEqual(fields, {"name", "email"})

    def test_iter_dirty_fields_empty(self):
        self.assertEqual(list(self.cache.iter_dirty_fields()), [])

    def test_dirty_entry_count(self):
        self.assertEqual(self.cache.dirty_entry_count(), 0)
        self.cache.mark_dirty("name", [1, 2])
        self.cache.mark_dirty("email", [3])
        self.assertEqual(self.cache.dirty_entry_count(), 3)

    def test_dirty_entry_count_after_pop(self):
        self.cache.mark_dirty("name", [1, 2])
        self.cache.mark_dirty("email", [3])
        self.cache.pop_dirty("name")
        self.assertEqual(self.cache.dirty_entry_count(), 1)

    def test_custom_dirty_factory(self):
        # OrderedSet-like types (any MutableSet with .update()) are typical
        from collections import OrderedDict

        class OrderedSet(set):
            """Minimal ordered set stand-in for testing."""

        cache = FieldCache(dirty_factory=OrderedSet)
        cache.mark_dirty("name", [1, 2])
        dirty = cache.get_dirty("name")
        self.assertIsInstance(dirty, OrderedSet)
        self.assertEqual(dirty, {1, 2})


class TestFieldCachePatches(unittest.TestCase):
    """Test deferred x2many patches."""

    def setUp(self):
        self.cache = FieldCache()

    def test_no_patches(self):
        self.assertIsNone(self.cache.get_patches("line_ids"))

    def test_add_and_get_patch(self):
        self.cache.add_patch("line_ids", 1, 100)
        self.cache.add_patch("line_ids", 1, 101)
        self.cache.add_patch("line_ids", 2, 200)

        patches = self.cache.get_patches("line_ids")
        self.assertEqual(patches[1], [100, 101])
        self.assertEqual(patches[2], [200])


class TestFieldCacheInvalidation(unittest.TestCase):
    """Test invalidation (per-field, per-id, all)."""

    def setUp(self):
        self.cache = FieldCache()
        self.cache.set_value("name", 1, "Alice")
        self.cache.set_value("name", 2, "Bob")
        self.cache.set_value("email", 1, "alice@x.com")

    def test_invalidate_field_all(self):
        self.cache.invalidate_field("name")
        self.assertFalse(self.cache.has_value("name", 1))
        self.assertFalse(self.cache.has_value("name", 2))
        # other field untouched
        self.assertTrue(self.cache.has_value("email", 1))

    def test_invalidate_field_specific_ids(self):
        self.cache.invalidate_field("name", [1])
        self.assertFalse(self.cache.has_value("name", 1))
        self.assertTrue(self.cache.has_value("name", 2))

    def test_invalidate_field_nonexistent(self):
        # should not raise
        self.cache.invalidate_field("nonexistent")
        self.cache.invalidate_field("nonexistent", [1])

    def test_invalidate_all(self):
        self.cache.invalidate_all()
        self.assertFalse(self.cache.has_value("name", 1))
        self.assertFalse(self.cache.has_value("email", 1))

    def test_invalidate_all_preserves_dirty(self):
        self.cache.mark_dirty("name", [1])
        self.cache.invalidate_all()
        # dirty flags survive invalidate_all
        self.assertTrue(self.cache.is_any_dirty())

    def test_clear_everything(self):
        self.cache.mark_dirty("name", [1])
        self.cache.add_patch("line_ids", 1, 100)
        self.cache.clear()
        self.assertFalse(self.cache.has_value("name", 1))
        self.assertFalse(self.cache.is_any_dirty())
        self.assertIsNone(self.cache.get_patches("line_ids"))


class TestFieldCacheIntrospection(unittest.TestCase):
    """Test iteration and repr."""

    def setUp(self):
        self.cache = FieldCache()

    def test_iter_fields_empty(self):
        self.assertEqual(list(self.cache.iter_fields()), [])

    def test_iter_fields(self):
        self.cache.set_value("name", 1, "Alice")
        self.cache.set_value("email", 1, "alice@x.com")
        fields = set(self.cache.iter_fields())
        self.assertEqual(fields, {"name", "email"})

    def test_iter_field_items(self):
        self.cache.set_value("name", 1, "Alice")
        items = list(self.cache.iter_field_items())
        self.assertEqual(len(items), 1)
        field, data = items[0]
        self.assertEqual(field, "name")
        self.assertEqual(data, {1: "Alice"})

    def test_has_field(self):
        self.assertFalse(self.cache.has_field("name"))
        self.cache.set_value("name", 1, "Alice")
        self.assertTrue(self.cache.has_field("name"))

    def test_repr(self):
        self.cache.set_value("name", 1, "Alice")
        self.cache.mark_dirty("name", [1])
        r = repr(self.cache)
        self.assertIn("fields=1", r)
        self.assertIn("dirty_entries=1", r)


class _MockField:
    """Minimal mock with model_name for pop_dirty_for_model tests."""

    def __init__(self, name, model_name):
        self.name = name
        self.model_name = model_name

    def __repr__(self):
        return f"<MockField {self.model_name}.{self.name}>"

    def __hash__(self):
        return hash((self.model_name, self.name))

    def __eq__(self, other):
        return (
            isinstance(other, _MockField)
            and self.model_name == other.model_name
            and self.name == other.name
        )


class TestPopDirtyForModel(unittest.TestCase):
    """Test pop_dirty_for_model() — filters by model_name attribute."""

    def setUp(self):
        self.cache = FieldCache()
        self.f_partner_name = _MockField("name", "res.partner")
        self.f_partner_email = _MockField("email", "res.partner")
        self.f_order_name = _MockField("name", "sale.order")

    def test_pops_matching_model(self):
        self.cache.mark_dirty(self.f_partner_name, [1, 2])
        self.cache.mark_dirty(self.f_partner_email, [3])
        self.cache.mark_dirty(self.f_order_name, [10])

        result = self.cache.pop_dirty_for_model("res.partner")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[self.f_partner_name], {1, 2})
        self.assertEqual(result[self.f_partner_email], {3})

        # sale.order dirty entry should remain
        self.assertTrue(self.cache.has_dirty_field(self.f_order_name))
        # res.partner entries should be gone
        self.assertFalse(self.cache.has_dirty_field(self.f_partner_name))
        self.assertFalse(self.cache.has_dirty_field(self.f_partner_email))

    def test_returns_empty_for_no_match(self):
        self.cache.mark_dirty(self.f_order_name, [10])
        result = self.cache.pop_dirty_for_model("res.partner")
        self.assertEqual(result, {})
        # sale.order still dirty
        self.assertTrue(self.cache.has_dirty_field(self.f_order_name))

    def test_returns_empty_when_no_dirty(self):
        result = self.cache.pop_dirty_for_model("res.partner")
        self.assertEqual(result, {})

    def test_skips_empty_id_sets(self):
        """Fields with empty dirty sets (after mark+pop) are excluded."""
        self.cache.mark_dirty(self.f_partner_name, [1])
        self.cache.pop_dirty(self.f_partner_name)
        # Re-add with empty set via defaultdict access
        _ = self.cache._dirty[self.f_partner_name]
        result = self.cache.pop_dirty_for_model("res.partner")
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
