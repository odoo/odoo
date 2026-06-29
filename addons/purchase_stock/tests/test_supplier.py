from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import tagged


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSupplier(TestStockCommon):
    _test_groups = None  # FIXME list needed groups

    def test_display_name(self):
        supplier = self.env['product.supplierinfo'].create({
            'partner_id': self.partner_1.id,  # Julia Agrolait
            'price': 123.0,
            'min_qty': 345,
            'delay': 1,
            'uom_id': self.uom_dozen.id,
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

    def test_missing_seller_does_not_crash_po_confirmation(self):
        """
        Ensure that when `_select_seller()` returns no seller because the merged
        procurement quantity is below vendor `min_qty`, the PO line update still
        succeeds and PO confirmation does not raise ZeroDivisionError.
        """
        product = self.env['product.product'].create({
            'name': 'Test Product',
        })
        vendor = self.env['product.supplierinfo'].create({
            'partner_id': self.partner.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'min_qty': 1,
            'price': 50,
        })
        values = {
            'supplier': vendor,
        }

        procurement = self.env['stock.rule'].Procurement(
            product,
            0.1,
            product.uom_id,
            self.stock_location,
            'Test 1',
            'TEST1',
            self.env.company,
            values,
        )
        self.env['stock.rule'].run([procurement])

        purchase_order = self.env['purchase.order'].search([
            ('partner_id', '=', self.partner.id),
        ])

        self.assertTrue(purchase_order)
        self.assertTrue(purchase_order.order_line)

        self.env['stock.rule'].run([procurement])
        purchase_order.button_confirm()  # should not raise ZeroDivisionError anymore

        self.assertEqual(purchase_order.state, 'purchase')
        self.assertRecordValues(purchase_order.order_line, [{
            'product_id': product.id,
            'product_qty': 0.2,
            'price_unit': 0.0,
            'uom_id': product.uom_id.id,
        }])
