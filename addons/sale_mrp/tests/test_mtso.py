from odoo.addons.mrp.tests.test_mtso import TestMrpMtso
from odoo.tools import float_compare


class TestSaleMrpMtso(TestMrpMtso):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_mtso_partial_availability(self):
        """When a MO is created from a SO through MTSO with partially available stock :
        Ensure the validation of the MO update the reserved value in the out picking rather
            than overwriting it with the produced value in order to fulfill the picking.
        When MO is not done AND product is not available in stock, increase of demand in SO should update existing MO.
        Either we have multiple sources for the same product, the same move is updated in the out picking. (until it's picked)
        """
        def assert_mo_count(count=1):
            self.assertEqual(len(self.MrpProduction.search([('product_id', '=', self.finished_product.id)])), count)

        # Set an available qty for 'Product M'
        self.StockQuantObj.create({
            'location_id': self.warehouse_1_step.lot_stock_id.id,
            'product_id': self.finished_product.id,
            'inventory_quantity': 4,
        }).action_apply_inventory()
        self.assertEqual(float_compare(self.finished_product.free_qty, 4, precision_rounding=2), 0)

        # Create sale order
        sale_form = Form(self.env['sale.order'])
        sale_form.partner_id = self.env['res.partner'].create({'name': 'Partner'})
        with sale_form.order_line.new() as line:
            line.name = self.finished_product.name
            line.product_id = self.finished_product
            line.product_uom_qty = 7.0
            line.product_uom = self.uom_unit
            line.price_unit = 2.0
        sale_order = sale_form.save()

        sale_order.action_confirm()
        delivery = sale_order.picking_ids
        mo = self.MrpProduction.search([('product_id', '=', self.finished_product.id)])
        assert_mo_count()

        self.assertEqual(len(delivery.move_ids), 1)
        self.assertEqual(float_compare(delivery.move_ids[0].quantity, 4, precision_rounding=2), 0)
        self.assertEqual(float_compare(delivery.move_ids[0].product_qty, 7, precision_rounding=2), 0)
        self.assertEqual(float_compare(mo.product_qty, 3, precision_rounding=2), 0)

        # Increase of initial demand in SO should update existing picking & MO (MO not done, Qty not available)
        sale_order.order_line[0].product_uom_qty = 10.0
        self.assertEqual(len(delivery.move_ids), 1)
        self.assertEqual(float_compare(delivery.move_ids[0].quantity, 4, precision_rounding=2), 0)  # Available qty didn't changed
        self.assertEqual(float_compare(delivery.move_ids[0].product_qty, 10, precision_rounding=2), 0)
        assert_mo_count()
        self.assertEqual(float_compare(mo.product_qty, 6, precision_rounding=2), 0)

        # Update product available Qty (+2), increase SO demand (+2), picking DO update, MO DOES NOT update (MO not done, Qty available)
        self.StockQuantObj.create({
            'location_id': self.warehouse_1_step.lot_stock_id.id,
            'product_id': self.finished_product.id,
            'inventory_quantity': 2,
        }).action_apply_inventory()
        self.assertEqual(float_compare(self.finished_product.free_qty, 2, precision_rounding=2), 0)

        sale_order.order_line[0].product_uom_qty = 12.0
        self.assertEqual(len(delivery.move_ids), 1)
        self.assertEqual(float_compare(delivery.move_ids[0].quantity, 6, precision_rounding=2), 0)
        self.assertEqual(float_compare(delivery.move_ids[0].product_qty, 12, precision_rounding=2), 0)
        assert_mo_count()
        self.assertEqual(float_compare(mo.product_qty, 6, precision_rounding=2), 0)  # Increased demand does not affect MO as qty is available in stock

        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        self.assertEqual(float_compare(delivery.move_ids[0].quantity, 12, precision_rounding=2), 0)


        # Increase SO demand creates new MO and update existing picking move (MO done, Qty not available)
        sale_order.order_line[0].product_uom_qty = 15.0
        self.assertEqual(len(delivery.move_ids), 1)
        self.assertEqual(float_compare(delivery.move_ids[0].quantity, 12, precision_rounding=2), 0)
        self.assertEqual(float_compare(delivery.move_ids[0].product_qty, 15, precision_rounding=2), 0)
        assert_mo_count(2)
        mo2 = self.MrpProduction.search([('product_id', '=', self.finished_product.id)]) - mo
        self.assertEqual(float_compare(mo.product_qty, 6, precision_rounding=2), 0)  # First MO not affected as it's done
        self.assertEqual(float_compare(mo2.product_qty, 3, precision_rounding=2), 0)

        mo2.button_mark_done()
        self.assertEqual(mo2.state, 'done')
        self.assertEqual(float_compare(delivery.move_ids[0].quantity, 15, precision_rounding=2), 0)
