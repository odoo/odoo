from odoo.http import request

from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):
    def cart_totals(self, **kwargs):
        cart_totals = super().cart_totals(**kwargs)
        cart_totals["country_code"] = request.website.company_id.country_code
        return cart_totals
