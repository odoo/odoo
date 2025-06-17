from datetime import timedelta

from odoo.fields import Datetime
from odoo.tools import lazy

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class TestProductRibbon(WebsiteSaleCommon):

    def setUp(self):
        super().setUp()
        # Manual ribbon
        self.manual_ribbon = self.env['product.ribbon'].create({
            'name': "Manual Ribbon",
            'assign': 'manual',
        })

        # Sale ribbon
        self.sale_ribbon = self.env['product.ribbon'].create({
            'name': "Sale Ribbon",
            'assign': 'sale',
        })

        # New ribbon
        self.new_ribbon = self.env['product.ribbon'].create({
            'name': "New Ribbon",
            'assign': 'new',
        })

    def test_manual_ribbon_assignment(self):
        self.product.website_ribbon_id = self.manual_ribbon.id
        products_prices = {self.product.id: {'base_price': 100, 'price_reduce': 100}}
        ribbon = self.product._get_ribbon(
            lambda product: lazy(lambda: products_prices[product.id]),
        )
        self.assertEqual(
            ribbon[self.product.id], self.manual_ribbon, "Manual ribbon should be returned",
        )

    def test_sale_ribbon_assignment(self):
        self.product.list_price = 100
        products_prices = {self.product.id: {'base_price': 100, 'price_reduce': 80}}  # discounted
        ribbon = self.product._get_ribbon(
            lambda product: lazy(lambda: products_prices[product.id]),
        )
        self.assertEqual(
            ribbon[self.product.id], self.sale_ribbon, "Sale ribbon should be returned",
        )

    def test_new_ribbon_assignment(self):
        self.product.publish_date = Datetime.now() - timedelta(days=10)
        products_prices = {self.product.id: {'base_price': 100, 'price_reduce': 100}}
        ribbon = self.product._get_ribbon(
            lambda product: lazy(lambda: products_prices[product.id]),
        )
        self.assertEqual(
            ribbon[self.product.id],
            self.new_ribbon,
            "New ribbon should be returned for recently published products",
        )

    def test_no_ribbon_if_none_match(self):
        self.product.publish_date = Datetime.now() - timedelta(days=100)
        products_prices = {self.product.id: {'base_price': 100, 'price_reduce': 100}}
        ribbon = self.product._get_ribbon(
            lambda product: lazy(lambda: products_prices[product.id]),
        )
        self.assertFalse(
            ribbon[self.product.id], "No ribbon should be returned when no condition is matched",
        )

    def test_ribbon_priority_assignment(self):
        self.product.website_ribbon_id = self.manual_ribbon.id
        self.product.publish_date = Datetime.now() - timedelta(days=10)
        products_prices = {self.product.id: {'base_price': 100, 'price_reduce': 80}}  # discounted
        self.sale_ribbon.sequence = 1
        self.new_ribbon.sequence = 2
        ribbon = self.product._get_ribbon(
            lambda product: lazy(lambda: products_prices[product.id]),
        )
        self.assertEqual(
            ribbon[self.product.id],
            self.manual_ribbon,
            "Manual ribbon should have the highest priority",
        )

        self.product.website_ribbon_id = False
        self.sale_ribbon.sequence = 1
        self.new_ribbon.sequence = 2
        ribbon = self.product._get_ribbon(
            lambda product: lazy(lambda: products_prices[product.id]),
        )
        self.assertEqual(
            ribbon[self.product.id],
            self.sale_ribbon,
            "Sale ribbon should have the highest priority",
        )

        self.new_ribbon.sequence = 1
        self.sale_ribbon.sequence = 2
        ribbon = self.product._get_ribbon(
            lambda product: lazy(lambda: products_prices[product.id]),
        )
        self.assertEqual(
            ribbon[self.product.id],
            self.new_ribbon,
            "New ribbon should have the highest priority",
        )
