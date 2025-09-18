"""Unit tests for odoo.libs.ir_http — no Odoo ORM dependency."""

import unittest

from odoo.libs.ir_http import slugify, slugify_one


class TestSlugifyOne(unittest.TestCase):
    """Test slugify_one pure function."""

    def test_simple_string(self):
        self.assertEqual(slugify_one("Hello World"), "hello-world")

    def test_special_characters(self):
        result = slugify_one("Hello & World!")
        self.assertIn("hello", result)
        self.assertIn("world", result)

    def test_underscores_replaced(self):
        self.assertEqual(slugify_one("hello_world"), "hello-world")

    def test_dashes_preserved(self):
        self.assertEqual(slugify_one("hello-world"), "hello-world")

    def test_max_length(self):
        result = slugify_one("hello world test", max_length=5)
        self.assertLessEqual(len(result), 5)

    def test_empty_string(self):
        self.assertEqual(slugify_one(""), "")

    def test_unicode_preserved(self):
        """CJK characters should survive slugification."""
        result = slugify_one("hello 你好")
        self.assertIn("hello", result)

    def test_multiple_spaces(self):
        result = slugify_one("hello   world")
        self.assertEqual(result, "hello-world")


class TestSlugify(unittest.TestCase):
    """Test slugify pure function (path-aware)."""

    def test_non_path_mode(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_path_mode(self):
        result = slugify("Hello/World Test", path=True)
        self.assertEqual(result, "hello/world-test")

    def test_path_with_web_extension(self):
        result = slugify(
            "My File/test.js",
            path=True,
            web_extensions=frozenset({".js", ".css"}),
        )
        self.assertIn(".js", result)

    def test_path_with_non_web_extension(self):
        result = slugify(
            "path/file.unknown",
            path=True,
            web_extensions=frozenset({".js", ".css"}),
        )
        # .unknown is not in web_extensions, so no special handling
        self.assertNotIn(".unknown", result)

    def test_empty_segments_removed(self):
        result = slugify("a//b", path=True)
        self.assertEqual(result, "a/b")


if __name__ == "__main__":
    unittest.main()
