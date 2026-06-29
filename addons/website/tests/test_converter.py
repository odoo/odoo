# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import get_db_name, BaseCase
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

        unslug = Registry(get_db_name())['ir.http']._unslug

        for slug, expected in tests.items():
            self.assertEqual(unslug(slug), expected, "%r case failed" % slug)

    def test_slug(self):
        tests = {
            'foo-1': (1, 'foo'),
            'foo-bar-1': (1, 'foo-bar'),
            'foo--1': (-1, 'foo'),
            '1-2': (2, '1'),
        }

        slug = Registry(get_db_name())['ir.http']._slug

        for expected, value in tests.items():
            self.assertEqual(slug(value), expected, "%r case failed" % (value,))


class TestTitleToSlug(BaseCase):
    """
    Those tests should pass with or without python-slugify
    See website/models/website.py slugify method
    """

    def _slugify(self, value):
        slugify = Registry(get_db_name())['ir.http']._slugify
        return slugify(value)

    def test_spaces(self):
        self.assertEqual(
            "spaces",
            self._slugify("   spaces   ")
        )

    def test_unicode(self):
        self.assertEqual(
            "hétérogénéité",
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
            "h-e-l-l-o",
            self._slugify("^h☺e$#!l(%l}o☞☞")
        )

    def test_str_to_unicode(self):
        self.assertEqual(
            "españa",
            self._slugify("España")
        )

    def test_numbers(self):
        self.assertEqual(
            "article-1",
            self._slugify("Article 1")
        )

    def test_non_ascii(self):
        self.assertEqual(
            "你好-再見",
            self._slugify("你好 再見")
        )

    def test_multiple_dashes(self):
        self.assertEqual(
            "d-a-sh-e-s",
            self._slugify("d-----a----sh--e-------s")
        )

    def test_leading_trailing_dashes_spaces_underscores(self):
        self.assertEqual(
            "mi-dd-le",
            self._slugify("_-__   -- -mi-dd-le- -- _ _-_- - ")
        )

    def test_normalized_composed(self):
        self.assertEqual(
            '\N{HANGUL SYLLABLE GA}',
            self._slugify('\N{HANGUL SYLLABLE GA}')
        )

    def test_normalized_decomposed(self):
        self.assertEqual(
            '\N{HANGUL SYLLABLE GA}',
            self._slugify('\N{HANGUL CHOSEONG KIYEOK}\N{HANGUL JUNGSEONG A}')
        )

    def test_all(self):
        self.assertEqual(
            "do-you-know-馬丁娜-à-la-海灘",
            self._slugify(" Do (YOU) ☞☞ know '馬丁娜 à la 海灘' ? ")
        )

    def test_slash_separator(self):
        self.assertEqual(
            "foo-bar",
            self._slugify("foo/bar")
        )

    def test_backslash_separator(self):
        self.assertEqual(
            "foo-bar",
            self._slugify(r"foo\bar")
        )

    def test_brackets(self):
        self.assertEqual(
            "black-chair-premium-with-matte-gold",
            self._slugify("Black chair(Premium, with matte gold)")
        )
