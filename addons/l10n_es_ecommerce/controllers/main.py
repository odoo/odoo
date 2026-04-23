# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import request, route
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleL10nEsEcommerce(WebsiteSale):

    @route()
    def portal_address_country_info(self, country, address_type, **kw):
        # The country-change refresh route doesn't forward the cart, which the
        # simplified-invoice VAT relaxation needs to read the order total.
        # Inject it here so the model stays free of any `request` dependency.
        kw.setdefault('order_sudo', request.cart)
        return super().portal_address_country_info(country, address_type, **kw)
