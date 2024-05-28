from odoo.addons.purchase_stock.tests.test_mtso import TestPurchaseMtso


class TestSalePurchaseMtso(TestPurchaseMtso):
    def create_so(self, warehouse, product, qty=1):
        return self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'warehouse_id': warehouse.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'price_unit': 1,
                'route_id': self.route_mtso.id,
            })],
        })

    def new_sale_line(self, sale_id, product, qty=1):
        self.env['sale.order.line'].create({
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'price_unit': 1,
            'route_id': self.route_mtso.id,
            'order_id': sale_id,
        })

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_mtso_so_po_1step(self):
        """
        TODO clean description, Integration Test (not unit)
        - set/increase/decrease SO demand (demand [<,>,=] stock) -> ignore/create/link & update PO
        - PO updates are smart (no < 0 qty)
        - Correctly assign & update picking in full or partial behavior
        - Flexibility of mtso assignation
        """
        warehouse = self.warehouse_1s
        customer_location = self.env.ref('stock.stock_location_customers')

        self.env['stock.quant']._update_available_quantity(self.productA, warehouse.lot_stock_id, 10)
        self.env['stock.quant']._update_available_quantity(self.productB, warehouse.lot_stock_id, 10)

        # Product is fully available, no PO created, SO's picking move is assigned
        so1 = self.create_so(warehouse, self.productA, 10)
        so1.action_confirm()
        self.assertRecordValues(so1.picking_ids, [{'location_id': warehouse.lot_stock_id.id, 'location_dest_id': customer_location.id}])
        so1_move = so1.picking_ids.move_ids
        self.assertEqual(len(so1_move), 1)
        self.assertAlmostEqual(so1_move.product_uom_qty, 10, 3)
        self.assertAlmostEqual(so1_move.quantity, 10, 3)
        self.assertEqual(so1_move.state, 'assigned')
        poA = so1._get_purchase_orders()
        self.assertFalse(poA)

        # Decrease qty : Still no PO, move correctly updated, still assigned
        so1.order_line.product_uom_qty = 8
        self.assertAlmostEqual(so1_move.product_uom_qty, 8, 3)
        self.assertAlmostEqual(so1_move.quantity, 8, 3)

        # Over Qty : A PO is created, PO_line qty is set to 2, SO's picking move is updated but remain unique anyway
        so1.order_line.product_uom_qty = 12
        so1_move = so1.picking_ids.move_ids
        poA = so1._get_purchase_orders()
        self.assertTrue(poA)
        self.assertEqual(poA.state, "draft")
        self.assertAlmostEqual(poA.order_line.product_uom_qty, 2, 3)
        self.assertEqual(len(so1_move), 1)
        # SO picking move has been updated
        self.assertAlmostEqual(so1_move.product_uom_qty, 12, 3)
        self.assertAlmostEqual(so1_move.quantity, 10, 3)  # The 10 in stock are already assigned
        self.assertEqual(so1_move.state, 'partially_available')

        # PO state is unchanged (not cancelled !), but PO_line qty is set to 0
        so1.order_line.product_uom_qty = 10
        self.assertEqual(poA.state, "draft")
        self.assertAlmostEqual(poA.order_line.product_uom_qty, 0, 3)

        # PO line do not decrease beneath 0
        so1.order_line.product_uom_qty = 8
        self.assertAlmostEqual(poA.order_line.product_uom_qty, 0, 3)

        # New SO requiring product from another Vendor : a new PO is created to fulfill missing quantity
        so2 = self.create_so(warehouse, self.productB, 15)
        so2.action_confirm()
        self.assertRecordValues(so2.picking_ids, [{'location_id': warehouse.lot_stock_id.id, 'location_dest_id': customer_location.id}])
        so2_prB_move = so2.picking_ids.move_ids
        self.assertAlmostEqual(so2_prB_move.product_uom_qty, 15, 3)
        self.assertAlmostEqual(so2_prB_move.quantity, 10, 3)
        self.assertEqual(so2_prB_move.state, 'partially_available')
        poB = so2._get_purchase_orders()
        self.assertTrue(poB)
        self.assertAlmostEqual(poB.order_line.product_uom_qty, 5, 3)
        # New sale line after confirm : MTSO still works
        # As poA already exist and is not done, rather than creating a new PO, so2 is linked to it
        self.new_sale_line(so2.id, self.productA, 6)
        self.assertEqual((poA | poB), so2._get_purchase_orders())
        # Reminder: only 8 out of 10 productA are assigned to so1, so it remains 2 available in stock
        so2_prA_move = so2.picking_ids.move_ids.filtered(lambda m: m.product_id.id == self.productA.id)
        self.assertAlmostEqual(poA.order_line.product_uom_qty, 4, 3)
        self.assertAlmostEqual(so2_prA_move.product_uom_qty, 6, 3)
        self.assertAlmostEqual(so2_prA_move.quantity, 2, 3)
        self.assertEqual(so2_prA_move.state, 'partially_available')

        # Confirm poA
        poA.button_confirm()
        self.assertEqual(poA.state, 'purchase')

        # Increase qty demand on so1 : new PO
        so1.order_line.product_uom_qty = 10
        so1.picking_ids.action_assign()
        self.assertAlmostEqual(so1_move.product_uom_qty, 10, 3)
        self.assertAlmostEqual(so1_move.quantity, 8, 3)  # There's enough qty of productA in stock, however, even with forced assign, none are free as 2 are reserved by so2
        self.assertEqual(so1_move.state, 'partially_available')
        self.assertEqual(so1.purchase_order_count, 2)  # As poA is already confirmed, a new PO is created for new demand
        poC = so1._get_purchase_orders() - poA

        # Whenever there's now 2 PO linked to so1, there's still only 1 move for its picking
        self.assertEqual(len(so1.picking_ids.move_ids), 1)
        self.assertAlmostEqual(poC.order_line.product_uom_qty, 2, 3)

        # Flexibility (1) : unreserve so2_prA_move, force assign and validate so1
        so2_prA_move._do_unreserve()
        so1.picking_ids.action_assign()  # All the quantity come from stock
        self.assertAlmostEqual(so1_move.product_uom_qty, 10, 3)
        self.assertAlmostEqual(so1_move.quantity, 10, 3)
        self.assertEqual(so1_move.state, 'assigned')
        self.assertTrue(so1.picking_ids.button_validate())
        # Flexibility (2) : confirm poA & poC, so2 is assigned successfully
        poA.picking_ids.button_validate()
        poC.button_confirm()
        poC.picking_ids.button_validate()  # poC is linked to so1, not to so2, however in MTSO it doesn't matter
        self.assertAlmostEqual(so2_prA_move.product_uom_qty, 6, 3)
        self.assertAlmostEqual(so2_prA_move.quantity, 6, 3)
        self.assertEqual(so2_prA_move.state, 'assigned')

        # Finally, complete poB and so2
        poB.button_confirm()
        poB.picking_ids.button_validate()
        self.assertAlmostEqual(so2_prB_move.product_uom_qty, 15, 3)
        self.assertAlmostEqual(so2_prB_move.quantity, 15, 3)
        self.assertEqual(so2_prB_move.state, 'assigned')
        self.assertTrue(so2.picking_ids.button_validate())

    def test_mtso_so_po_old_3steps_delivery(self):
        """Verify correct transitive qty on procurement and assignation"""
        warehouse = self.warehouse_3s
        warehouse.write({'reception_steps': 'one_step'})
        stock_location = warehouse.lot_stock_id
        pack_location = warehouse.wh_pack_stock_loc_id
        output_location = warehouse.wh_output_stock_loc_id

        pick_r, pack_r, ship_r = warehouse.delivery_route_id.rule_ids
        pack_r.write({
            'action': 'pull',  # have to force 'pull' again as setting 'one_step' on reception updated this rule
            'procure_method': 'mts_else_mto'})
        ship_r.write({
            'action': 'pull',
            'procure_method': 'mts_else_mto',
            'sequence': pick_r.sequence - 1,
        })
        pick_mtso_r = self.route_mtso.rule_ids.filtered(lambda r: r.picking_type_id.id == warehouse.pick_type_id.id)
        pick_mtso_r.write({'location_dest_id': pack_location.id})

        self.env['stock.quant']._update_available_quantity(self.productA, stock_location, 1)
        self.env['stock.quant']._update_available_quantity(self.productA, pack_location, 2)
        self.env['stock.quant']._update_available_quantity(self.productA, output_location, 3)

        so = self.create_so(warehouse, self.productA, 10)
        so.action_confirm()
        pick_p, pack_p, ship_p = so.picking_ids
        pick_m, pack_m, ship_m = so.picking_ids.move_ids
        po = so._get_purchase_orders()
        self.assertTrue(po)
        self.assertAlmostEqual(po.order_line.product_uom_qty, 4, 3)
        self.assertAlmostEqual(pick_m.product_uom_qty, 5, 3)
        self.assertAlmostEqual(pick_m.quantity, 1, 3)  # The 1 in stock is already assigned
        self.assertEqual(pick_m.state, 'partially_available')
        self.assertAlmostEqual(pack_m.product_uom_qty, 7, 3)
        self.assertAlmostEqual(pack_m.quantity, 2, 3)
        self.assertEqual(pack_p.move_ids.state, 'partially_available')
        self.assertAlmostEqual(ship_m.product_uom_qty, 10, 3)
        self.assertAlmostEqual(ship_m.quantity, 3, 3)
        self.assertEqual(ship_p.move_ids.state, 'partially_available')

        po.button_confirm()
        po.picking_ids.button_validate()
        self.assertAlmostEqual(pick_m.quantity, 5, 3)
        self.assertEqual(pick_m.state, 'assigned')
        self.assertTrue(pick_p.button_validate())

        self.assertAlmostEqual(pack_m.quantity, 7, 3)
        self.assertEqual(pack_m.state, 'assigned')
        self.assertTrue(pack_p.button_validate())

        self.assertAlmostEqual(ship_m.quantity, 10, 3)
        self.assertEqual(ship_m.state, 'assigned')
        self.assertTrue(ship_p.button_validate())
