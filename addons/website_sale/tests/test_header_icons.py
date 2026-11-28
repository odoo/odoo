# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html as lxml_html

from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestHeaderIcons(WebsiteSaleCommon, HttpCase):

    def _get_header_icons(self, name):
        tree = lxml_html.fromstring(self.url_open("/").content)
        return {
            (icon.get("data-icon"), "oi-filled" in icon.classes)
            for icon in tree.xpath(f"//i[@data-header-icon='{name}']")
        }

    def test_the_header_cart_and_wishlist_icons_are_the_ones_stored_on_the_website(self):
        tree = lxml_html.fromstring(self.url_open("/").content)
        for icon in tree.xpath("//i[@data-header-icon='cart' or @data-header-icon='wishlist']"):
            self.assertIn("o_not_editable", icon.classes, "Header icons should be out of the savable areas")
        self.assertEqual(self._get_header_icons("cart"), {("shopping_cart", False)}, "The default cart icon should be outlined")
        self.assertEqual(self._get_header_icons("wishlist"), {("favorite", True)}, "The default wishlist icon should be a filled heart")

        # The test user is not a website designer.
        website = self.website.with_user(self.env.ref("base.user_admin"))
        website.set_header_icons({
            "cart": {"icon": "shopping_bag", "filled": True},
            "wishlist": {"icon": "bookmark", "filled": False},
        })

        self.assertEqual(self._get_header_icons("cart"), {("shopping_bag", True)}, "The header should render the stored cart icon")
        self.assertEqual(self._get_header_icons("wishlist"), {("bookmark", False)}, "The header should render the stored wishlist icon")
