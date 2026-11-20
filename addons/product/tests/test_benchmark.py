import logging
from unittest import SkipTest

from odoo import fields
from odoo.tests import BenchmarkCase

_logger = logging.getLogger(__name__)


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

        _logger.info(
            'Benchmark dataset product.benchmark_pricelists: products=%s pricelists=%s',
            len(cls.products), len(cls.pricelists),
        )

    def test_prices(self):
        """Compute prices for all selected products in every selected pricelist."""
        for pricelist in self.pricelists:
            pricelist._get_products_price(self.products, quantity=10, date=self.pricing_date)

    def test_prices_after_update(self):
        """Recompute prices after a list-price change; exclude the write and its flush."""
        self.products.write({'list_price': 123.0})
        with self.measure():
            for pricelist in self.pricelists:
                pricelist._get_products_price(self.products, quantity=10, date=self.pricing_date)
