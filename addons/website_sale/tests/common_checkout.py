# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import root
from odoo.tests.common import HttpCase

from odoo.addons.website_sale.models.website import CART_SESSION_CACHE_KEY
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class CheckoutCommon(WebsiteSaleCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_address_values = {
            'name': 'a res.partner address',
            'email': 'email@email.email',
            'street': 'ooo',
            'city': 'ooo',
            'zip': '1200',
            'country_id': cls.country_be.id,
            'phone': '+333333333333333',
        }

    def authenticate_with_cart(self, user, password, browser=None, cart_id=None):
        session = super().authenticate(user, password, browser=browser)
        session[CART_SESSION_CACHE_KEY] = cart_id or self.cart.id
        root.session_store.save(session)
        return session
