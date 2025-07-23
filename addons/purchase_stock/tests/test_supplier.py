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

    def test_effective_vendor(self):
        route = self.env['stock.route'].create({
            'name': 'Buy',
            'rule_ids': [
                (0, 0, {
                    'name': 'Buy',
                    'location_dest_id': self.stock_location.id,
                    'action': 'buy',
                    'picking_type_id': self.picking_type_in.id,
                }),
            ],
        })

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.productA.id,
            'product_min_qty': 2,
            'product_max_qty': 4,
        })
        # The Buy route is not set on the product -> no effective vendor
        self.assertFalse(orderpoint.effective_vendor_id)

        self.productA.write({
            'route_ids': [(4, route.id)],
        })
        self.env.invalidate_all()
        # The route is set, but there is no supplier -> no effective vendor
        self.assertFalse(orderpoint.effective_vendor_id)

        self.env['product.supplierinfo'].create({
            'product_id': self.productA.id,
            'partner_id': self.partner_1.id,
            'min_qty': 10,
            'price': 50,
        })

        self.env.invalidate_all()
        # The route is set and there is a supplier -> effective vendor is available
        self.assertEqual(orderpoint.effective_vendor_id, self.partner_1)
        self.assertEqual(orderpoint.supplier_id_placeholder, 'Julia Agrolait (10.0 Units - $\xa050.00)')
        # The actual vendor remains empty
        self.assertFalse(orderpoint.supplier_id)
