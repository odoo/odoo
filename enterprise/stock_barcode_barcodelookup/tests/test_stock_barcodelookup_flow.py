from odoo.tests import tagged
from ...product_barcodelookup.tests.test_barcodelookup_flow import TestBarcodelookup


@tagged('post_install', '-at_install')
class TestStockBarcodeBarcodelookup(TestBarcodelookup):

    def test_01_stock_barcode_barcodelookup_tour(self):
        with self.mockBarcodelookupAutofill():
            self.start_tour("/web", 'StockBarcodeBarcodelookupFlow', login="admin")
            product = self.env['product.template'].sudo().search([('name', '=', 'Odoo Scale up')], limit=1)
            self._verify_product_data(product, normalized_view=True)
