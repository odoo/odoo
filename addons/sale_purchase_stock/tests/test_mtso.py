from odoo.addons.purchase_stock.tests.test_mtso import TestPurchaseMtso


class TestSalePurchaseMtso(TestPurchaseMtso):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_mtso_and_qty_decreasing(self):
        """
        First, confirm a SO that has a line with the MTO route (the product
        should already be available in stock). Then, decrease the qty on the SO
        line:
        - The delivery should be updated
        - There should not be any other picking
        """
        warehouse = self.warehouse_1_step
        customer_location = self.env.ref('stock.stock_location_customers')
        mto_route = self.mts_route

        self.product_a.type = 'product'
        self.env['stock.quant']._update_available_quantity(self.product_a, warehouse.lot_stock_id, 10)

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'warehouse_id': warehouse.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 10,
                'product_uom': self.product_a.uom_id.id,
                'price_unit': 1,
                'route_id': mto_route.id,
            })],
        })
        so.action_confirm()
        self.assertRecordValues(so.picking_ids, [{'location_id': warehouse.lot_stock_id.id, 'location_dest_id': customer_location.id}])

        so.order_line.product_uom_qty = 8
        self.assertRecordValues(so.picking_ids, [{'location_id': warehouse.lot_stock_id.id, 'location_dest_id': customer_location.id}])
        self.assertEqual(so.picking_ids.move_ids.product_uom_qty, 8)
