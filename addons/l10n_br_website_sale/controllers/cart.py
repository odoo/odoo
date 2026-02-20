from odoo.http import request, route

from odoo.addons.website_sale.controllers.cart import Cart as WebsiteSaleCart


class Cart(WebsiteSaleCart):

    @route()
    def cart_totals(self):
        cart_totals = super().cart_totals()

        cart_totals['country_code'] = request.website.company_id.country_code

        return cart_totals
