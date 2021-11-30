from odoo.tests import tagged

from odoo.addons.base.tests.common import PerformanceCommon


@tagged('post_install', '-at_install')
class TestSalePerformance(PerformanceCommon):

    def test_batch_creation_sale_orders(self):
        """Enforce sale.order create overrides always support batch creation"""
        self.assertModelCreateMulti('sale.order')

    def test_batch_creation_sale_order_line(self):
        """Enforce sale.order.line create overrides always support batch creation"""
        self.assertModelCreateMulti('sale.order.line')
