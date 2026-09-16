# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests.common import BaseCase
from odoo.tools import file_open

from odoo.addons.web.icons import ICONS, search_icons


class TestIcons(BaseCase):

    def test_icons_metadata_list(self):
        """
        `icons.py` is generated with `generate_icons.py`.
        This test ensures that the icons listed in `ICONS` match the combined
        set of icons from the wishlist and the Odoo UI icons configuration.
        """

        with (
            file_open('web/tooling/icons/icons_wishlist.txt') as wishlist_file,
            file_open('web/tooling/icons/odoo_ui_icons_config.json') as config_file,
        ):
            wishlist = {
                line.strip() for line in wishlist_file
                if line.strip() and not line.startswith('#')
            }

            config = json.load(config_file)
            odoo_ui_icons = {
                config['css_prefix_text'] + icon['css']
                for icon in config['glyphs'] if icon.get('selected', True)
            }
            self.assertEqual(set(ICONS), wishlist | odoo_ui_icons)

    def test_icons_search(self):
        self.assertEqual(
            [name for name, _has_fill in search_icons()], list(ICONS),
            "an empty needle matches every icon",
        )
        self.assertEqual(
            next(search_icons('shopping cart')), ('shopping_cart', True),
            "every word of the needle must match, and has_fill comes along",
        )
        self.assertFalse(
            list(search_icons('shopping zzzz')),
            "a single unmatched word is enough to discard an icon",
        )

    def test_icons_search_is_case_and_accent_insensitive(self):
        expected = list(search_icons('shopping cart'))
        self.assertTrue(expected)
        self.assertEqual(list(search_icons('SHOPPING Cart')), expected)
        self.assertEqual(list(search_icons('shöpping cârt')), expected)

    def test_icons_search_translated(self):
        """Translated tags are searched on top of the English ones, and are
        normalized the same way, so an unaccented needle matches them."""
        def translate(tags):
            return 'chariot de marché' if tags == ICONS['shopping_cart']['tags'] else ''

        self.assertEqual(
            list(search_icons('marche', translate)), [('shopping_cart', True)],
            "an unaccented needle matches an accented translated tag",
        )
        self.assertEqual(
            next(search_icons('shopping cart', translate)), ('shopping_cart', True),
            "English tags stay searchable whatever the language",
        )
