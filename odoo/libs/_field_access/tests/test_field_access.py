"""Unit tests for field cache access accelerator.

Tests both the Rust extension and pure-Python fallback with mock
dicts and sentinel objects — no Odoo ORM dependency.
"""

import enum
import unittest

from odoo.libs._field_access._fallback import (
    batch_cache_filter,
    batch_cache_get,
    batch_cache_values,
    scalar_cache_get,
)


class MockSentinel(enum.Enum):
    SENTINEL = -1
    PENDING = -2


SENTINEL = MockSentinel.SENTINEL
PENDING = MockSentinel.PENDING


class _FieldAccessTestMixin:
    """Shared tests — subclassed once for Rust, once for fallback."""

    batch_cache_get = None
    batch_cache_filter = None
    batch_cache_values = None
    scalar_cache_get = None

    # --- batch_cache_get ---

    def test_batch_get_all_hit(self):
        cache = {1: "a", 2: "b", 3: "c"}
        results, misses = self.batch_cache_get(cache, (1, 2, 3), PENDING, False)
        self.assertEqual(list(results), ["a", "b", "c"])
        self.assertEqual(list(misses), [])

    def test_batch_get_none_becomes_none_val(self):
        cache = {1: None, 2: "x"}
        results, misses = self.batch_cache_get(cache, (1, 2), PENDING, False)
        self.assertEqual(list(results), [False, "x"])
        self.assertEqual(list(misses), [])

    def test_batch_get_pending_is_miss(self):
        cache = {1: PENDING, 2: "ok"}
        results, misses = self.batch_cache_get(cache, (1, 2), PENDING, 0)
        self.assertEqual(list(results), [0, "ok"])
        self.assertEqual(list(misses), [0])

    def test_batch_get_missing_key_is_miss(self):
        cache = {1: "a"}
        results, misses = self.batch_cache_get(cache, (1, 2, 3), PENDING, "")
        self.assertEqual(list(results), ["a", "", ""])
        self.assertEqual(list(misses), [1, 2])

    def test_batch_get_empty(self):
        results, misses = self.batch_cache_get({}, (), PENDING, False)
        self.assertEqual(list(results), [])
        self.assertEqual(list(misses), [])

    def test_batch_get_false_is_valid(self):
        """False is a valid cache value, not a miss."""
        cache = {1: False}
        results, misses = self.batch_cache_get(cache, (1,), PENDING, False)
        self.assertEqual(list(results), [False])
        self.assertEqual(list(misses), [])

    def test_batch_get_zero_is_valid(self):
        """0 is a valid cache value, not a miss."""
        cache = {1: 0}
        results, misses = self.batch_cache_get(cache, (1,), PENDING, 0)
        self.assertEqual(list(results), [0])
        self.assertEqual(list(misses), [])

    def test_batch_get_all_miss(self):
        results, misses = self.batch_cache_get({}, (1, 2, 3), PENDING, -1)
        self.assertEqual(list(results), [-1, -1, -1])
        self.assertEqual(list(misses), [0, 1, 2])

    def test_batch_get_mixed(self):
        cache = {1: "a", 3: None, 5: PENDING}
        results, misses = self.batch_cache_get(cache, (1, 2, 3, 4, 5), PENDING, False)
        self.assertEqual(list(results), ["a", False, False, False, False])
        self.assertEqual(list(misses), [1, 3, 4])

    # --- batch_cache_filter ---

    def test_filter_truthy_values(self):
        cache = {1: "yes", 2: "", 3: 42, 4: 0, 5: None}
        passing, misses = self.batch_cache_filter(cache, (1, 2, 3, 4, 5), PENDING)
        self.assertEqual(list(passing), [1, 3])
        self.assertEqual(list(misses), [])

    def test_filter_pending_is_miss(self):
        cache = {1: PENDING, 2: "ok"}
        passing, misses = self.batch_cache_filter(cache, (1, 2), PENDING)
        self.assertEqual(list(passing), [2])
        self.assertEqual(list(misses), [0])

    def test_filter_missing_key_is_miss(self):
        cache = {1: "ok"}
        passing, misses = self.batch_cache_filter(cache, (1, 2), PENDING)
        self.assertEqual(list(passing), [1])
        self.assertEqual(list(misses), [1])

    def test_filter_empty(self):
        passing, misses = self.batch_cache_filter({}, (), PENDING)
        self.assertEqual(list(passing), [])
        self.assertEqual(list(misses), [])

    def test_filter_all_falsy(self):
        cache = {1: 0, 2: "", 3: False, 4: None}
        passing, misses = self.batch_cache_filter(cache, (1, 2, 3, 4), PENDING)
        self.assertEqual(list(passing), [])
        self.assertEqual(list(misses), [])

    def test_filter_all_truthy(self):
        cache = {1: "a", 2: 1, 3: True}
        passing, misses = self.batch_cache_filter(cache, (1, 2, 3), PENDING)
        self.assertEqual(list(passing), [1, 2, 3])
        self.assertEqual(list(misses), [])

    # --- batch_cache_values ---

    def test_values_all_hit(self):
        cache = {1: "a", 2: "b", 3: "c"}
        result = self.batch_cache_values(cache, (1, 2, 3), PENDING)
        self.assertEqual(list(result), ["a", "b", "c"])

    def test_values_miss_returns_none(self):
        cache = {1: "a"}
        result = self.batch_cache_values(cache, (1, 2), PENDING)
        self.assertIsNone(result)

    def test_values_pending_returns_none(self):
        cache = {1: PENDING, 2: "ok"}
        result = self.batch_cache_values(cache, (1, 2), PENDING)
        self.assertIsNone(result)

    def test_values_empty(self):
        result = self.batch_cache_values({}, (), PENDING)
        self.assertEqual(list(result), [])

    def test_values_none_is_valid(self):
        """None is a valid cache value — not a miss."""
        cache = {1: None, 2: "x"}
        result = self.batch_cache_values(cache, (1, 2), PENDING)
        self.assertEqual(list(result), [None, "x"])

    def test_values_false_is_valid(self):
        """False is a valid cache value — not a miss."""
        cache = {1: False, 2: 0}
        result = self.batch_cache_values(cache, (1, 2), PENDING)
        self.assertEqual(list(result), [False, 0])

    def test_values_early_bailout(self):
        """Should bail on first miss, not process remaining IDs."""
        cache = {1: "a"}  # id 2 missing
        result = self.batch_cache_values(cache, (1, 2, 3), PENDING)
        self.assertIsNone(result)

    # --- scalar_cache_get ---

    def test_scalar_hit(self):
        field = object()
        env_dict = {"_field_cache_memo": {field: {42: "value"}}}
        result = self.scalar_cache_get(env_dict, field, 42, PENDING, SENTINEL)
        self.assertEqual(result, "value")

    def test_scalar_miss_no_memo(self):
        result = self.scalar_cache_get({}, "f", 42, PENDING, SENTINEL)
        self.assertIs(result, SENTINEL)

    def test_scalar_miss_no_field(self):
        env_dict = {"_field_cache_memo": {}}
        result = self.scalar_cache_get(env_dict, "f", 42, PENDING, SENTINEL)
        self.assertIs(result, SENTINEL)

    def test_scalar_miss_no_id(self):
        field = object()
        env_dict = {"_field_cache_memo": {field: {}}}
        result = self.scalar_cache_get(env_dict, field, 42, PENDING, SENTINEL)
        self.assertIs(result, SENTINEL)

    def test_scalar_pending_returns_sentinel(self):
        field = object()
        env_dict = {"_field_cache_memo": {field: {42: PENDING}}}
        result = self.scalar_cache_get(env_dict, field, 42, PENDING, SENTINEL)
        self.assertIs(result, SENTINEL)

    def test_scalar_none_is_valid(self):
        """None is a valid cache value, not a miss."""
        field = object()
        env_dict = {"_field_cache_memo": {field: {42: None}}}
        result = self.scalar_cache_get(env_dict, field, 42, PENDING, SENTINEL)
        self.assertIsNone(result)

    def test_scalar_false_is_valid(self):
        """False is a valid cache value, not a miss."""
        field = object()
        env_dict = {"_field_cache_memo": {field: {42: False}}}
        result = self.scalar_cache_get(env_dict, field, 42, PENDING, SENTINEL)
        self.assertIs(result, False)

    def test_scalar_zero_is_valid(self):
        field = object()
        env_dict = {"_field_cache_memo": {field: {42: 0}}}
        result = self.scalar_cache_get(env_dict, field, 42, PENDING, SENTINEL)
        self.assertEqual(result, 0)


class TestFallback(_FieldAccessTestMixin, unittest.TestCase):
    """Test pure-Python fallback implementations."""

    @classmethod
    def setUpClass(cls):
        cls.batch_cache_get = staticmethod(batch_cache_get)
        cls.batch_cache_filter = staticmethod(batch_cache_filter)
        cls.batch_cache_values = staticmethod(batch_cache_values)
        cls.scalar_cache_get = staticmethod(scalar_cache_get)


class TestAccelerated(_FieldAccessTestMixin, unittest.TestCase):
    """Test Rust extension — skipped if not installed.

    scalar_cache_get always uses the Python fallback (PyO3 boundary
    overhead exceeds savings on the hit path), so only batch functions
    are imported from Rust.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from odoo_rust import (
                batch_cache_filter,
                batch_cache_get,
                batch_cache_values,
            )
        except ImportError:
            raise unittest.SkipTest("odoo_rust Rust extension not installed")
        cls.batch_cache_get = staticmethod(batch_cache_get)
        cls.batch_cache_filter = staticmethod(batch_cache_filter)
        cls.batch_cache_values = staticmethod(batch_cache_values)
        cls.scalar_cache_get = staticmethod(scalar_cache_get)


if __name__ == "__main__":
    unittest.main()
