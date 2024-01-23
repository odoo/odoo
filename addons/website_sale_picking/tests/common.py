# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment_custom.tests.common import PaymentCustomCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class OnsiteCommon(PaymentCustomCommon, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create onsite carrier
        product = cls._prepare_carrier_product(list_price=0.0)
        cls.carrier = cls._prepare_carrier(
            product,
            fixed_price=0.0,
            delivery_type='onsite',
            name="Example shipping On Site")
        cls.provider = cls._prepare_provider('onsite')
