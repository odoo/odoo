# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests.common import HttpCase, TransactionCase, tagged
from odoo.tools.translate import LazyGettext

from odoo.addons.html_editor.tools import icons_catalog, search_icons, translated_icon_tags
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
        translations = {
            ICONS['shopping_cart']['tags']._source: 'chariot de marché',
            ICONS['star']['tags']._source: 'étoile',
        }

        def translate(tags, lang=''):
            return translations.get(tags._source, '')

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
            self.assertCountEqual(
                search_icons(env, 'eto'), ['alt_route', 'bluetooth', 'star'],
                "a needle matches the translated tags of an icon and the English tags of another",
            )


class TestIconsCatalog(TransactionCase):

    def test_icons_catalog(self):
        catalog = icons_catalog('en_US')
        self.assertEqual([icon['name'] for icon in catalog], list(ICONS))
        shopping_cart = next(icon for icon in catalog if icon['name'] == 'shopping_cart')
        self.assertEqual(shopping_cart['has_fill'], ICONS['shopping_cart']['has_fill'])
        self.assertEqual(
            shopping_cart['tags'], ICONS['shopping_cart']['tags']._source.split('|'),
            "the English tags are listed one by one",
        )

    def test_icons_catalog_translated(self):
        """Translated tags follow the English ones, without duplicates."""
        def translate(tags, lang=''):
            if tags._source == ICONS['star']['tags']._source:
                return 'étoile|star'
            return tags._source

        icons_catalog.cache_clear()
        self.addCleanup(icons_catalog.cache_clear)
        with patch.object(LazyGettext, '_translate', translate):
            catalog = {icon['name']: icon for icon in icons_catalog('fr_FR')}
        english_tags = ICONS['star']['tags']._source.split('|')
        self.assertIn('star', english_tags)
        self.assertEqual(catalog['star']['tags'], [*english_tags, 'étoile'])
        self.assertEqual(
            catalog['shopping_cart']['tags'],
            ICONS['shopping_cart']['tags']._source.split('|'),
            "untranslated tags are not repeated",
        )


@tagged('-at_install', 'post_install')
class TestIconsRoute(HttpCase):

    def test_icons_route(self):
        self.authenticate('admin', 'admin')
        catalog = self.make_jsonrpc_request('/html_editor/icons', {'lang': 'en_US'})
        self.assertEqual(catalog, icons_catalog('en_US'))
        self.assertEqual(
            self.make_jsonrpc_request('/html_editor/icons', {'lang': '../xx'}), catalog,
            "an inactive language falls back to the user's one",
        )
