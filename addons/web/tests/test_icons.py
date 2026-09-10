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

    def test_icons_search_translated(self):
        def translate(tags):
            return 'chariot de marché' if tags == ICONS['shopping_cart']['tags'] else ''

        self.assertEqual(
            list(search_icons('marché', translate)), [('shopping_cart', True)],
            "the translated tags are searched on top of the English ones",
        )
        self.assertEqual(
            next(search_icons('shopping cart', translate)), ('shopping_cart', True),
            "English tags stay searchable whatever the language",
        )
