# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction


@tagged('post_install', '-at_install')
class TestPickingBarcodeClientAction(TestBarcodeClientAction):
    def test_create_product_from_barcode_lookup(self):
        self.picking_type_in.restrict_scan_product = 'mandatory'
        self.assertFalse(self.env['product.product'].search([('barcode', '=', '510002952387')], limit=1))
        self.start_tour('/odoo/barcode', 'test_create_product_from_barcode_lookup', login='admin')
        self.assertTrue(self.env['product.product'].search([('barcode', '=', '510002952387')], limit=1))
