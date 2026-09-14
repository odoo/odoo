import time

from odoo.tests.common import BaseCase

from odoo.addons.integration.tools.session_cache import SessionCache


class TestSessionCache(BaseCase):
    def setUp(self):
        super().setUp()
        self.cache = SessionCache(max_size=3, ttl_hours=0.001)

    def test_cache_set_get(self):
        self.cache.set("key1", "value1")
        result = self.cache.get("key1")

        self.assertEqual(result, "value1")

    def test_cache_miss(self):
        result = self.cache.get("nonexistent")

        self.assertIsNone(result)

    def test_cache_expiration(self):
        self.cache.set("key1", "value1")

        time.sleep(4)

        result = self.cache.get("key1")

        self.assertIsNone(result)

    def test_cache_lru_eviction(self):
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")

        self.cache.set("key4", "value4")

        self.assertIsNone(self.cache.get("key1"))

        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")
        self.assertEqual(self.cache.get("key4"), "value4")

    def test_cache_lru_order(self):
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")

        self.cache.get("key1")

        self.cache.set("key4", "value4")

        self.assertEqual(self.cache.get("key1"), "value1")

        self.assertIsNone(self.cache.get("key2"))

    def test_cache_invalidate_single(self):
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        self.cache.invalidate("key1")

        self.assertIsNone(self.cache.get("key1"))
        self.assertEqual(self.cache.get("key2"), "value2")

    def test_cache_invalidate_all(self):
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        self.cache.invalidate_all()

        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))

    def test_cache_stats(self):
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        stats = self.cache.get_stats()

        self.assertEqual(stats["size"], 2)
        self.assertEqual(stats["max_size"], 3)
        self.assertAlmostEqual(stats["ttl_hours"], 0.001, places=3)
