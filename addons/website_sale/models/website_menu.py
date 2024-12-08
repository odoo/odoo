# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    def _compute_visible(self):
        """ Hide '/shop' menus to the public user if only logged-in users can access it. """
        shop_menus = self.filtered(lambda m: m.url[:5] == '/shop')
        for menu in shop_menus:
            menu.is_visible = menu.website_id.has_ecommerce_access()

        return super(WebsiteMenu, self - shop_menus)._compute_visible()
