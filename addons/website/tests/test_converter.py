# Part of Odoo. See LICENSE file for full copyright and licensing details.
import threading

from odoo.tests.common import BaseCase
from odoo.modules.registry import Registry


class TestSlugUnslug(BaseCase):

    def test_unslug(self):
        tests = {
            '': (None, None),
            'foo': (None, None),
            'foo-': (None, None),
            '-': (None, None),
            'foo-1': ('foo', 1),
            'foo-bar-1': ('foo-bar', 1),
            'foo--1': ('foo', -1),
            '1': (None, 1),
            '1-1': ('1', 1),
            '--1': (None, None),
            'foo---1': (None, None),
            'foo1': (None, None),
            # qs & anchor & trailing slash
            'foo-1/': ('foo', 1),
            'foo-1/?qs=1': ('foo', 1),
            'foo-1/#anchor': ('foo', 1),
            'foo-1?qs=1': ('foo', 1),
            'foo-1#anchor': ('foo', 1),
        }

        unslug = Registry(threading.current_thread().dbname)['ir.http']._unslug

        for slug, expected in tests.items():
            self.assertEqual(unslug(slug), expected, "%r case failed" % slug)

    def test_slug(self):
        tests = {
            'foo-1': (1, 'foo'),
            'foo-bar-1': (1, 'foo-bar'),
            'foo--1': (-1, 'foo'),
            '1-2': (2, '1'),
        }

        slug = Registry(threading.current_thread().dbname)['ir.http']._slug

        for expected, value in tests.items():
            self.assertEqual(slug(value), expected, "%r case failed" % (value,))


class TestTitleToSlug(BaseCase):
    """
    Those tests should pass with or without python-slugify
    See website/models/website.py slugify method
    """

    def _slugify(self, value):
        _slugify = Registry(threading.current_thread().dbname)['ir.http']._slugify
        return _slugify(value)

    def test_spaces(self):
        self.assertEqual(
            "spaces",
            self._slugify("   spaces   ")
        )

    def test_unicode(self):
        self.assertEqual(
            "heterogeneite",
            self._slugify("hétérogénéité")
        )

    def test_underscore(self):
        self.assertEqual(
            "one-two",
            self._slugify("one_two")
        )

    def test_caps(self):
        self.assertEqual(
            "camelcase",
            self._slugify("CamelCase")
        )

    def test_special_chars(self):
        self.assertEqual(
            "o-d-o-o",
            self._slugify(r"o!#d{|\o/@~o&%^?")
        )

    def test_str_to_unicode(self):
        self.assertEqual(
            "espana",
            self._slugify("España")
        )

    def test_numbers(self):
        self.assertEqual(
            "article-1",
            self._slugify("Article 1")
        )

    def test_all(self):
        self.assertEqual(
            "do-you-know-martine-a-la-plage",
            self._slugify("Do YOU know 'Martine à la plage' ?")
        )
