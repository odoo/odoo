# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):
    def cart_totals(self, order_sudo) -> dict:
        """Override to only show the total, taxes included, to Brazilian companies."""
        cart_totals = super().cart_totals(order_sudo=order_sudo)
        if request.website.company_id.country_code == "BR":
            cart_totals["show_untaxed_amount"] = False
            cart_totals["show_tax_lines"] = False
        return cart_totals
