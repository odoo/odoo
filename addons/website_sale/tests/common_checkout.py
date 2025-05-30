# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import root
from odoo.tests.common import HttpCase

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.models.website import CART_SESSION_CACHE_KEY
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class CheckoutCommon(WebsiteSaleCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_id = cls.country_be.id
        cls.user_portal = cls._create_new_portal_user()
        cls.user_internal = cls._create_new_internal_user()
        cls.user_internal.partner_id.company_id = cls.env.company

    def setUp(self):
        super().setUp()
        self.WebsiteSaleController = WebsiteSale()
        self.default_address_values = {
            'name': 'a res.partner address',
            'email': 'email@email.email',
            'street': 'ooo',
            'city': 'ooo',
            'zip': '1200',
            'country_id': self.country_id,
            'phone': '+333333333333333',
            'address_type': 'delivery',
        }
        self.default_billing_address_values = dict(
            self.default_address_values, address_type='billing',
        )

    def authenticate_with_cart(self, user, password, browser=None, cart_id=None):
        session = super().authenticate(user, password, browser=browser)
        session[CART_SESSION_CACHE_KEY] = cart_id or self.cart.id
        root.session_store.save(session)
        return session
