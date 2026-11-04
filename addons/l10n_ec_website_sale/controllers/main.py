# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale


class L10nEcWebsiteSale(WebsiteSale):

    @route()
    def portal_address_country_info(self, country, address_type, **kw):
        # The country-change refresh route doesn't forward the cart, which the Cédula limit reads.
        kw.setdefault('order_sudo', request.cart)
        return super().portal_address_country_info(country, address_type, **kw)
