# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.tools.translate import LazyGettext

from odoo.addons.html_editor.tools import search_icons, translated_icon_tags
from odoo.addons.web.icons import ICONS


class TestIconsSearch(TransactionCase):

    def test_icons_search(self):
        self.assertEqual(
            list(search_icons(self.env)), list(ICONS),
            "an empty needle matches every icon",
        )
        self.assertIn(
            'shopping_cart', list(search_icons(self.env, 'shopping cart')),
            "a needle matches the name of an icon as well as its tags",
        )
        self.assertFalse(
            list(search_icons(self.env, 'shopping zzzz')),
            "a single unmatched word is enough to discard an icon",
        )

    def test_icons_search_is_case_and_accent_insensitive(self):
        expected = list(search_icons(self.env, 'shopping cart'))
        self.assertTrue(expected)
        self.assertEqual(list(search_icons(self.env, 'SHOPPING Cart')), expected)
        self.assertEqual(list(search_icons(self.env, 'shöpping cârt')), expected)

    def test_icons_search_translated(self):
        """Translated tags are searched on top of the English ones, and are
        normalized the same way, so an unaccented needle matches them."""
        def translate(tags, lang=''):
            return 'chariot de marché' if tags is ICONS['shopping_cart']['tags'] else ''

        self.env['res.lang']._activate_lang('fr_FR')
        env = self.env(context={'lang': 'fr_FR'})
        # the fake translations must not outlive the test in the cache
        translated_icon_tags.cache_clear()
        self.addCleanup(translated_icon_tags.cache_clear)
        with patch.object(LazyGettext, '_translate', translate):
            self.assertEqual(
                list(search_icons(env, 'marche')), ['shopping_cart'],
                "an unaccented needle matches an accented translated tag",
            )
            self.assertIn(
                'shopping_cart', list(search_icons(env, 'shopping cart')),
                "English tags stay searchable whatever the language",
            )
