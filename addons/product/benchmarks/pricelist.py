from unittest import SkipTest

from odoo import fields
from odoo.tests import BenchmarkCase, benchmark


class BenchmarkPricelist(BenchmarkCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        blueprint = cls.env.ref('product.benchmark_pricelists', raise_if_not_found=False)
        if not blueprint:
            msg = "Required blueprint product.benchmark_pricelists is missing"
            raise SkipTest(msg)

        cls.products = blueprint._get_populated('price_products')
        cls.pricelists = blueprint._get_populated('price_pricelists')
        if not cls.products or not cls.pricelists:
            msg = "The product population has no products or pricelists"
            raise SkipTest(msg)
        cls.pricing_date = fields.Date.today()

    @benchmark
    def prices(self):
        for pricelist in self.pricelists:
            pricelist._get_products_price(self.products, quantity=10, date=self.pricing_date)

    @benchmark
    def prices_after_update(self):
        self.products.write({'list_price': 123.0})
        with self.measure():
            for pricelist in self.pricelists:
                pricelist._get_products_price(self.products, quantity=10, date=self.pricing_date)
