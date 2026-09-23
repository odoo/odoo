import unittest

from odoo.tools.cache import ormcache


class TestOrmcacheUnknownKwargs(unittest.TestCase):
    def test_known_bucket_is_accepted(self):
        self.assertEqual(ormcache("self.id", cache="stable").cache_name, "stable")

    def test_default_bucket_is_the_default(self):
        self.assertEqual(ormcache("self.id").cache_name, "default")

    def test_unknown_bucket_still_raises(self):
        with self.assertRaises(ValueError) as caught:
            ormcache("self.id", cache="nope")
        self.assertIn("unknown cache", str(caught.exception))

    def test_a_misspelt_cache_keyword_raises(self):
        for typo in ("cach", "chache", "caches"):
            with self.subTest(typo=typo), self.assertRaises(TypeError):
                ormcache("self.id", **{typo: "stable"})  # type: ignore[arg-type]

    def test_an_invented_keyword_raises(self):
        with self.assertRaises(TypeError):
            ormcache("self.id", lru_size=99)  # type: ignore[call-arg]


def _shadows_the_method(self, __ormcache_method, value):
    return value


def _shadows_a_default(self, __ormcache_default_0, value=1):
    return value


class TestOrmcacheKeyShadowing(unittest.TestCase):
    def test_a_parameter_cannot_shadow_the_method(self):
        with self.assertRaises(ValueError) as caught:
            ormcache("value")(_shadows_the_method)
        self.assertIn("reserved", str(caught.exception))

    def test_a_parameter_cannot_shadow_a_generated_default(self):
        with self.assertRaises(ValueError):
            ormcache("value")(_shadows_a_default)

    def test_an_ordinary_signature_is_unaffected(self):
        def compute(self, value, flag=True):
            return value

        key = ormcache("value")(compute).__cache__.key  # type: ignore[attr-defined]
        self.assertTrue(callable(key))


if __name__ == "__main__":
    unittest.main()
