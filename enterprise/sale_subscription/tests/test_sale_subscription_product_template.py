# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Command
from odoo.tests import tagged, users

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged('post_install', '-at_install')
class TestSaleSubscriptionProductTemplate(TestSubscriptionCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.subscription_product = cls._create_product(
            product_subscription_pricing_ids=[
                Command.create({'plan_id': cls.plan_week.id, 'price': 5}),
                Command.create({'plan_id': cls.plan_month.id, 'price': 15}),
            ],
        )

    @users('salesman')
    def test_sale_subscription_get_configurator_display_price(self):
        configurator_price = self.env['product.template']._get_configurator_display_price(
            product_or_template=self.subscription_product,
            quantity=3,
            date=datetime(2000, 1, 1),
            currency=self.currency,
            pricelist=self.pricelist,
            plan_id=self.plan_month.id,
        )

        self.assertEqual(configurator_price[0], 15)

    @users('salesman')
    def test_sale_subscription_get_additional_configurator_data(self):
        configurator_data = self.env['product.template']._get_additional_configurator_data(
            product_or_template=self.subscription_product,
            date=datetime(2000, 1, 1),
            currency=self.currency,
            pricelist=self.pricelist,
            plan_id=self.plan_month.id,
        )

        self.assertEqual(configurator_data['price_info'], "per month")
