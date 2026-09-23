import unittest

from odoo.libs.collections.misc import Collector, StackMap


class TestCollector(unittest.TestCase):
    def test_discard_accepts_generator(self):
        c: Collector = Collector()
        c["a"] = (1, 2)
        c["b"] = (3,)
        c.discard_keys_and_values(x for x in (1, 3))
        self.assertEqual(c["a"], (2,))
        self.assertEqual(c["b"], ())

    def test_discard_removes_keys_and_values(self):
        c: Collector = Collector()
        c["a"] = (1, 2)
        c["k"] = (2, 3)
        c.discard_keys_and_values(["a", 2])
        self.assertNotIn("a", c)
        self.assertEqual(c["k"], (3,))


class TestStackMapLen(unittest.TestCase):
    def test_shadowed_key_counted_once(self):
        sm = StackMap({"a": 1})
        sm.push_map({"a": 2, "b": 3})
        self.assertEqual(len(sm), 2)
        self.assertEqual(dict(sm), {"a": 2, "b": 3})

    def test_len_matches_iteration(self):
        sm = StackMap({"a": 1, "b": 2})
        sm.push_map({"b": 20, "c": 30})
        sm.push_map({"c": 300})
        self.assertEqual(len(sm), len(set(sm)))
        self.assertEqual(len(sm), 3)

    def test_empty(self):
        self.assertEqual(len(StackMap()), 0)
        self.assertEqual(len(StackMap({})), 0)

    def test_topmost_wins_and_popmap_restores(self):
        sm = StackMap({"a": 1})
        sm.push_map({"a": 2})
        self.assertEqual(sm["a"], 2)
        sm.pop_map()
        self.assertEqual(sm["a"], 1)
        self.assertEqual(len(sm), 1)


if __name__ == "__main__":
    unittest.main()


class TestDotDictProtocols(unittest.TestCase):
    def test_a_dunder_probe_sees_no_attribute(self):
        import markupsafe

        from odoo.libs.collections import DotDict

        value = DotDict(a=1)
        self.assertFalse(hasattr(value, "__html__"))
        self.assertEqual(str(markupsafe.escape(value)), "{&#39;a&#39;: 1}")
        self.assertEqual(value.a, 1)
        self.assertIsNone(value.missing)
