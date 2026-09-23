import unittest

from odoo.libs.lru import LRU


class TestLRU(unittest.TestCase):
    def test_shrink_keeps_most_recent(self):
        cache: LRU = LRU(10)
        for i in range(10):
            cache[i] = i
        cache.count = 3
        self.assertEqual(len(cache), 3)
        self.assertEqual(sorted(cache.keys()), [7, 8, 9])

    def test_shrink_respects_recent_access(self):
        cache: LRU = LRU(5)
        for i in range(5):
            cache[i] = i
        _ = cache[0]
        cache.count = 2
        self.assertEqual(len(cache), 2)
        self.assertIn(0, cache)

    def test_count_must_be_positive(self):
        cache: LRU = LRU(5)
        with self.assertRaises(ValueError):
            cache.count = 0


class TestLRURepr(unittest.TestCase):
    def test_repr_reports_occupancy(self):
        lru = LRU(10, [(i, i) for i in range(3)])
        self.assertEqual(repr(lru), "LRU(count=10, size=3, gen=0)")

    def test_repr_tracks_clear_generation(self):
        lru = LRU(4, [(1, "a")])
        lru.clear()
        self.assertEqual(repr(lru), "LRU(count=4, size=0, gen=1)")

    def test_repr_does_not_leak_contents(self):
        lru = LRU(4, [("secret-key", "secret-value")])
        self.assertNotIn("secret", repr(lru))

    def test_repr_uses_the_actual_class_name(self):
        class Sub(LRU):
            pass

        self.assertTrue(repr(Sub(2)).startswith("Sub("))


class TestLRUEviction(unittest.TestCase):
    def test_capacity_eviction_reports_the_evicted_pair(self):
        evicted = []
        lru = LRU(2, on_evict=lambda k, v: evicted.append((k, v)))
        lru["a"], lru["b"], lru["c"] = 1, 2, 3
        self.assertEqual(evicted, [("a", 1)])

    def test_shrinking_the_count_reports_every_eviction(self):
        evicted = []
        lru = LRU(
            3, [(i, i) for i in range(3)], on_evict=lambda k, v: evicted.append(k)
        )
        lru.count = 1
        self.assertEqual(evicted, [0, 1])

    def test_a_generation_guarded_store_evicts_too(self):
        evicted = []
        lru = LRU(1, [("a", 1)], on_evict=lambda k, v: evicted.append(k))
        self.assertTrue(lru.set_if_generation("b", 2, lru.generation))
        self.assertEqual(evicted, ["a"])

    def test_overwrite_pop_and_clear_are_not_evictions(self):
        evicted = []
        lru = LRU(2, [("a", 1), ("b", 2)], on_evict=lambda k, v: evicted.append(k))
        lru["a"] = 3
        lru.pop("b")
        lru.clear()
        self.assertEqual(evicted, [])


if __name__ == "__main__":
    unittest.main()
