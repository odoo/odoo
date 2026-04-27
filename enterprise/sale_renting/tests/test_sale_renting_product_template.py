# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Command
from odoo.tests import tagged, users

from odoo.addons.sale_renting.tests.common import SaleRentingCommon


@tagged('post_install', '-at_install')
class TestSaleRentingProductTemplate(SaleRentingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.rental_product = cls._create_product(
            product_pricing_ids=[
                Command.create({'recurrence_id': cls.recurrence_hour.id, 'price': 5}),
                Command.create({'recurrence_id': cls.recurrence_day.id, 'price': 15}),
            ],
        )

    @users('salesman')
    def test_sale_renting_get_configurator_display_price(self):
        configurator_price = self.env['product.template']._get_configurator_display_price(
            product_or_template=self.rental_product,
            quantity=3,
            date=datetime(2000, 1, 1),
            currency=self.currency,
            pricelist=self.pricelist,
            start_date=datetime(2000, 1, 1),
            end_date=datetime(2000, 1, 3),
        )

        self.assertEqual(configurator_price[0], 30)

    @users('salesman')
    def test_sale_renting_get_additional_configurator_data(self):
        configurator_data = self.env['product.template']._get_additional_configurator_data(
            product_or_template=self.rental_product,
            date=datetime(2000, 1, 1),
            currency=self.currency,
            pricelist=self.pricelist,
            start_date=datetime(2000, 1, 1),
            end_date=datetime(2000, 1, 3),
        )

        self.assertEqual(configurator_data['price_info'], "2 Days")
