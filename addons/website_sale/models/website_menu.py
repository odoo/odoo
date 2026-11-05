# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    def _compute_visible(self):
        """Hide '/shop' menus to the public user if only logged-in users can access it."""
        super()._compute_visible()
        for menu in self.filtered(lambda m: m.url[:5] == "/shop"):
            if menu.is_visible and not menu.website_id.has_ecommerce_access():
                menu.is_visible = False
