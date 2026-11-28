# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class TestShopMenuDisabled(WebsiteSaleCommon):
    def _shop_menu_visible(self):
        menu = self.env.ref(self.website._website_xmlid("website_sale.menu_shop"))
        menu = menu.with_user(self.public_user)
        menu.invalidate_recordset(["is_visible"])
        with MockRequest(menu.env, website=self.website):
            return menu.is_visible

    def test_shop_menu_hidden_when_website_sale_disabled(self):
        # baseline: the Shop menu is visible to the public
        self.assertTrue(self._shop_menu_visible())

        # disable website_sale on this website -> Shop menu hidden for the public
        module = self.env["ir.module.module"]._get("website_sale")
        self.website.sudo().disabled_module_ids = [Command.link(module.id)]
        self.assertFalse(self._shop_menu_visible())

        # re-enabling restores it
        self.website.sudo().disabled_module_ids = [Command.unlink(module.id)]
        self.assertTrue(self._shop_menu_visible())
