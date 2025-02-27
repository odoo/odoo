from odoo.addons.stock.tests.common import TestStockCommon


class TestSupplier(TestStockCommon):
    def test_display_name(self):
        supplier = self.env['product.supplierinfo'].create({
            'partner_id': self.partner_1.id,  # Julia Agrolait
            'price': 123.0,
            'min_qty': 345,
            'delay': 1,
            'product_uom_id': self.uom_dozen.id,
            'product_id': self.product_1.id,
        })

        self.assertEqual(supplier.display_name, 'Julia Agrolait (345.0 Dozens - $\xa0123.00)')
        self.assertEqual(supplier.with_context(use_simplified_supplier_name=True).display_name, 'Julia Agrolait')
