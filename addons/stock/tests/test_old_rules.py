# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.addons.stock.models.stock_rule import StockRule
from odoo.tests import Form
from odoo.addons.stock.tests.common import TestStockCommon

class TestOldRules(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Partner'})

        # Since the old rules are still a valid setup for multi-step routes, we need to make sure they still work.
        # Create a warehouse with 3 steps using old rules setup so we need to restore it only once.
        cls.warehouse_3_steps = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 3 steps',
            'code': '3S',
            'reception_steps': 'three_steps',
            'delivery_steps': 'pick_pack_ship',
        })
        delivery_route_3 = cls.warehouse_3_steps.delivery_route_id
        delivery_route_3.rule_ids[0].write({
            'location_dest_id': delivery_route_3.rule_ids[1].location_src_id.id,
        })
        delivery_route_3.rule_ids[1].write({'action': 'pull'})
        delivery_route_3.rule_ids[2].write({'action': 'pull'})
        reception_route_3 = cls.warehouse_3_steps.reception_route_id
        reception_route_3.rule_ids[0].write({
            'location_src_id': reception_route_3.rule_ids[1].location_dest_id.id,
        })
        reception_route_3.rule_ids[1].write({'action': 'pull_push'})
        reception_route_3.rule_ids[2].write({'action': 'pull_push'})


        # Create a warehouse with 2 steps using old rules setup.
        cls.warehouse_2_steps = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 2 steps',
            'code': '2S',
            'reception_steps': 'two_steps',
            'delivery_steps': 'pick_ship',
        })
        delivery_route_2 = cls.warehouse_2_steps.delivery_route_id
        delivery_route_2.rule_ids[0].write({
            'location_dest_id': delivery_route_2.rule_ids[1].location_src_id.id,
            'name': '2S: Stock → Output',
        })
        delivery_route_2.rule_ids[1].write({'action': 'pull'})

    def test_delay_alert_3_old(self):
        partner_demo_customer = self.partner
        final_location = partner_demo_customer.property_stock_customer
        self.env['stock.rule'].run([
            StockRule.Procurement(
                self.productA,
                4.0,
                self.productA.uom_id,
                final_location,
                'delay',
                'delay',
                self.warehouse_3_steps.company_id,
                {
                    'warehouse_id': self.warehouse_3_steps,
                }
            ),
        ])
        ship, pack, pick = self.env['stock.move'].search([('product_id', '=', self.productA.id)])
        # by default they all the same `date`
        self.assertEqual(set((ship + pack + pick).mapped('date')), {pick.date})

        # pick - pack - ship
        ship.date += timedelta(days=2)
        pack.date += timedelta(days=1)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertFalse(ship.delay_alert_date)

        # move the pack after the ship
        # pick - ship - pack
        pack.date += timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertTrue(ship.delay_alert_date)
        self.assertAlmostEqual(ship.delay_alert_date, pack.date)

        # restore the pack before the ship
        # pick - pack - ship
        pack.date -= timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertFalse(ship.delay_alert_date)

        # move the pick after the pack
        # pack - ship - pick
        pick.date += timedelta(days=3)
        self.assertFalse(pick.delay_alert_date)
        self.assertTrue(pack.delay_alert_date)
        self.assertFalse(ship.delay_alert_date)
        self.assertAlmostEqual(pack.delay_alert_date, pick.date)

        # move the ship before the pack
        # ship - pack - pick
        ship.date -= timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertTrue(pack.delay_alert_date)
        self.assertTrue(ship.delay_alert_date)
        self.assertAlmostEqual(pack.delay_alert_date, pick.date)
        self.assertAlmostEqual(ship.delay_alert_date, pack.date)

        # move the pack at the end
        # ship - pick - pack
        pack.date = pick.date + timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertTrue(ship.delay_alert_date)
        self.assertAlmostEqual(ship.delay_alert_date, pack.date)

        # fix the ship
        ship.date = pack.date + timedelta(days=2)
        self.assertFalse(pick.delay_alert_date)
        self.assertFalse(pack.delay_alert_date)
        self.assertFalse(ship.delay_alert_date)

    def test_mtso(self):
        """ Run a procurement for 5 products when there are only 4 in stock then
        check that MTS is applied on the moves when the rule is set to 'mts_else_mto'
        Also ensure the whole stock is emptied and only the needed quantity is propagated.
        """
        partner_demo_customer = self.partner
        final_location = partner_demo_customer.property_stock_customer

        self.env['stock.quant']._update_available_quantity(self.productA, self.warehouse_3_steps.wh_output_stock_loc_id, 4.0)

        # We set quantities in the stock location to avoid warnings
        # triggered by '_onchange_product_id_check_availability'
        self.env['stock.quant']._update_available_quantity(self.productA, self.warehouse_3_steps.lot_stock_id, 4.0)

        # We alter one rule and we set it to 'mts_else_mto'
        self.warehouse_3_steps.delivery_route_id.rule_ids.filtered(
            lambda r: r.procure_method == "make_to_order"
        ).procure_method = 'mts_else_mto'

        reference = self.env['stock.reference'].create({'name': 'Test-pg-mtso-mto'})

        self.env['stock.rule'].run([
            StockRule.Procurement(
                self.productA,
                5.0,
                self.productA.uom_id,
                final_location,
                'test_mtso_mto',
                'test_mtso_mto',
                self.warehouse_3_steps.company_id,
                {
                    'warehouse_id': self.warehouse_3_steps,
                    'reference_ids': reference,
                }
            )
        ])

        qty_available = self.env['stock.quant']._get_available_quantity(self.productA, self.warehouse_3_steps.wh_output_stock_loc_id)

        # 3 pickings should be created.
        picking_ids = self.env['stock.picking'].search([('reference_ids', 'in', reference.id)])
        self.assertEqual(len(picking_ids), 3)
        for picking in picking_ids:
            self.assertEqual(picking.move_ids.procure_method, 'make_to_stock')
            self.assertEqual(len(picking.move_ids), 1)
        self.assertRecordValues(picking_ids.move_ids, [
            {'product_qty': 5, 'procure_method': 'make_to_stock'},
            {'product_qty': 1, 'procure_method': 'make_to_stock'},
            {'product_qty': 1, 'procure_method': 'make_to_stock'},
        ])
        self.assertEqual(qty_available, 0, 'The 4 products should still be available')

    def test_mtso_multi_pg(self):
        """ Run 3 procurements for 2 products at the same times when there are 4 in stock then
        check that MTS is applied on the moves when the rule is set to 'mts_else_mto'
        """
        warehouse = self.warehouse_3_steps
        partner_demo_customer = self.partner
        final_location = partner_demo_customer.property_stock_customer
        product_a = self.env['product.product'].create({
            'name': 'ProductA',
            'is_storable': True,
        })

        self.env['stock.quant']._update_available_quantity(product_a, warehouse.wh_output_stock_loc_id, 4.0)

        # We alter one rule and we set it to 'mts_else_mto'
        self.warehouse_3_steps.delivery_route_id.rule_ids.filtered(
            lambda r: r.procure_method == "make_to_order"
        ).procure_method = 'mts_else_mto'

        reference_1 = self.env['stock.reference'].create({'name': 'Test-pg-mtso-mts-1'})
        reference_2 = self.env['stock.reference'].create({'name': 'Test-pg-mtso-mts-2'})
        reference_3 = self.env['stock.reference'].create({'name': 'Test-pg-mtso-mts-3'})

        self.env['stock.rule'].run([
            StockRule.Procurement(
                product_a,
                2.0,
                product_a.uom_id,
                final_location,
                'test_mtso_mts_1',
                'test_mtso_mts_1',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'reference_ids': reference_1,
                }
            ),
            StockRule.Procurement(
                product_a,
                2.0,
                product_a.uom_id,
                final_location,
                'test_mtso_mts_2',
                'test_mtso_mts_2',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'reference_ids': reference_2,
                }
            ),
            StockRule.Procurement(
                product_a,
                2.0,
                product_a.uom_id,
                final_location,
                'test_mtso_mts_3',
                'test_mtso_mts_3',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'reference_ids': reference_3,
                }
            )
        ])

        pickings_pg1 = self.env['stock.picking'].search([('reference_ids', 'in', reference_1.id)])
        pickings_pg2 = self.env['stock.picking'].search([('reference_ids', 'in', reference_2.id)])
        pickings_pg3 = self.env['stock.picking'].search([('reference_ids', 'in', reference_3.id)])

        # The 2 first procurements should have create only 1 picking since enough quantities
        # are left in the delivery location
        self.assertEqual(len(pickings_pg1), 1)
        self.assertEqual(len(pickings_pg2), 1)
        self.assertEqual(pickings_pg1.move_ids.procure_method, 'make_to_stock')
        self.assertEqual(pickings_pg2.move_ids.procure_method, 'make_to_stock')

        # The last one should have 3 pickings as there's nothing left in the delivery location
        self.assertEqual(len(pickings_pg3), 3)
        for picking in pickings_pg3:
            # Only the picking from Stock to Pack should be MTS
            self.assertEqual(picking.move_ids.procure_method, 'make_to_stock')

            # All the moves should be should have the same quantity as it is on each procurements
            self.assertEqual(len(picking.move_ids), 1)
            self.assertEqual(picking.move_ids.product_uom_qty, 2)

    def test_2_steps_and_backorder(self):
        """ When creating a backorder with a package, the latter should be reserved in the new picking. Moreover,
         the initial picking shouldn't have any line about this package """
        def create_picking(pick_type, from_loc, to_loc):
            picking = self.env['stock.picking'].create({
                'picking_type_id': pick_type.id,
                'location_id': from_loc.id,
                'location_dest_id': to_loc.id,
                'state': 'draft',
            })
            move_A, move_B = self.env['stock.move'].create([{
                'product_id': self.productA.id,
                'product_uom_qty': 1,
                'product_uom': self.productA.uom_id.id,
                'picking_id': picking.id,
                'location_id': from_loc.id,
                'location_dest_id': to_loc.id,
            }, {
                'product_id': self.productB.id,
                'product_uom_qty': 1,
                'product_uom': self.productB.uom_id.id,
                'picking_id': picking.id,
                'location_id': from_loc.id,
                'location_dest_id': to_loc.id,
            }])
            picking.action_confirm()
            picking.action_assign()
            return picking, move_A, move_B

        pick_type = self.warehouse_2_steps.pick_type_id
        delivery_type = self.warehouse_2_steps.out_type_id
        customer_location = delivery_type.default_location_dest_id

        self.env['stock.quant']._update_available_quantity(self.productA, self.warehouse_2_steps.lot_stock_id, 1)
        self.env['stock.quant']._update_available_quantity(self.productB, self.warehouse_2_steps.lot_stock_id, 1)

        picking, moveA, moveB = create_picking(pick_type, pick_type.default_location_src_id, pick_type.default_location_dest_id)
        moveA.picked = True
        picking.action_put_in_pack()
        moveB.picked = True
        picking.action_put_in_pack()
        picking.button_validate()
        picking, _, _ = create_picking(delivery_type, delivery_type.default_location_src_id, customer_location)
        packB = picking.move_ids[1].move_line_ids.package_id
        picking.move_ids[0].picked = True

        action_data = picking.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(action_data['context'])).save()
        backorder_wizard.process()
        bo = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])

        self.assertNotIn(packB, picking.move_line_ids.package_id)
        self.assertEqual(packB, bo.move_line_ids.package_id)
        self.assertEqual(bo.move_ids.state, 'assigned')

    def test_pack_delivery_three_step_propagate_package_consumable_old(self):
        """ Checks all works right in the following case:
          * For a three-step delivery
          * Put products in a package then validate the receipt.
          * The automatically generated internal transfer should have package set by default.
        """
        prod = self.env['product.product'].create({'name': 'bad dragon', 'type': 'consu'})
        ship_move = self.env['stock.move'].create({
            'product_id': prod.id,
            'product_uom_qty': 5.0,
            'product_uom': prod.uom_id.id,
            'location_id': self.warehouse_3_steps.wh_output_stock_loc_id.id,
            'location_dest_id': self.customer_location.id,
            'warehouse_id':  self.warehouse_3_steps.id,
            'picking_type_id':  self.warehouse_3_steps.out_type_id.id,
            'procure_method': 'make_to_order',
            'state': 'draft',
        })

        # create chained pick/pack moves to test with
        ship_move._assign_picking()
        ship_move._action_confirm()
        pack_move = ship_move.move_orig_ids[0]
        pick_move = pack_move.move_orig_ids[0]

        picking = pick_move.picking_id
        picking.action_confirm()
        picking.action_put_in_pack()
        self.assertTrue(picking.move_line_ids.result_package_id)
        picking.button_validate()
        self.assertEqual(pack_move.move_line_ids.result_package_id, picking.move_line_ids.result_package_id)

    def test_report_reception_4_pick_pack(self):
        """ Check that reception report ignores outgoing moves that are not beginning of chain
        """

        warehouse = self.warehouse_3_steps
        self.product = self.env['product.product'].create({
            'name': 'Test product',
            'is_storable': True,
        })

        ship_move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom_qty': 5.0,
            'product_uom': self.product.uom_id.id,
            'location_id': warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': self.customer_location.id,
            'warehouse_id': warehouse.id,
            'picking_type_id': warehouse.out_type_id.id,
            'procure_method': 'make_to_order',
            'state': 'draft',
        })

        # create chained pick/pack moves to test with
        ship_move._assign_picking()
        ship_move._action_confirm()
        pack_move = ship_move.move_orig_ids[0]
        pick_move = pack_move.move_orig_ids[0]

        self.assertEqual(pack_move.state, 'waiting', "Pack move wasn't created...")
        self.assertEqual(pick_move.state, 'confirmed', "Pick move wasn't created...")

        receipt_form = Form(self.env['stock.picking'], view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = warehouse.in_type_id
        with receipt_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 15
        receipt = receipt_form.save()

        report = self.env['report.stock.report_reception']
        report_values = report._get_report_values(docids=[receipt.id])
        self.assertEqual(len(report_values['sources_to_lines']), 1, "There should only be 1 line (pick move)")

    def test_update_picking_origin(self):
        """ Check that adding new moves to a picking updates its origin without duplicate nor order mismatch
        """

        moves = self.env['stock.move'].create([
            {
                'picking_type_id': self.warehouse_1.out_type_id.id,
                'location_id': self.warehouse_1.lot_stock_id.id,
                'location_dest_id': self.customer_location.id,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': 1.0,
                'origin': origin,
            } for product, origin in [(self.productA, 'origin1'), (self.productA, 'origin2'), (self.productB, 'origin2'), (self.productB, 'origin1')]
        ])
        moves[0]._action_confirm()
        receipt = moves.picking_id
        self.assertEqual(receipt.origin, 'origin1')
        moves[1:]._action_confirm()
        self.assertEqual(receipt.origin, 'origin1,origin2')

    def test_propagate_cancel_in_pull_setup(self):
        """
        Check the cancellation propagation in pull set ups.
        """
        # create a procurement group
        product1 = self.env['product.product'].create({
            'name': 'test_procurement_cancel_propagation',
            'is_storable': True,
        })
        pick_pack_ship_route = self.warehouse_3_steps.delivery_route_id
        pick_rule = pick_pack_ship_route.rule_ids.filtered(lambda rule: rule.picking_type_id == self.warehouse_3_steps.pick_type_id)
        pack_rule = pick_pack_ship_route.rule_ids.filtered(lambda rule:  rule.picking_type_id == self.warehouse_3_steps.pack_type_id)
        (pick_rule | pack_rule).propagate_cancel = True
        ship_rule = pick_pack_ship_route.rule_ids - (pick_rule | pack_rule)
        self.env['stock.rule'].run([
            self.env['stock.rule'].Procurement(
                product1,
                1.0,
                product1.uom_id,
                ship_rule.location_dest_id,
                'test_mtso_mts_1',
                'test_mtso_mts_1',
                self.warehouse_3_steps.company_id,
                {
                    'warehouse_id': self.warehouse_3_steps,
                }
            ),
        ])
        move_chain = self.env['stock.move'].search([('product_id', '=', product1.id)])
        self.assertEqual(len(move_chain), 3)
        pick_move = move_chain.filtered(lambda m: m.picking_type_id == self.warehouse_3_steps.pick_type_id)
        pick_move.picking_id.action_cancel()
        self.assertEqual(move_chain.mapped('state'), ['cancel', 'cancel', 'cancel'])

    def test_negative_move_with_take_loc_from_rule(self):
        """
        This test checks if t a negative move will be merged correctly when the loc_dest_id
        is taken from the rule instead of the picking type.
        """
        rule = self.warehouse_1.reception_route_id.rule_ids.filtered(lambda r: r.action == 'pull')
        new_loc = self.env['stock.location'].create({
            'name': 'Shelf',
            'usage': 'transit',
            'location_id': rule.location_dest_id.id,
        })
        rule.write({
            'location_dest_id': new_loc.id,
        })
        rule.location_dest_from_rule = True
        picking = self.env['stock.picking'].create({
            'picking_type_id': rule.picking_type_id.id,
            'location_dest_id': rule.location_dest_id.id,
        })
        pos_move = self.env['stock.move'].create({
            'product_id': self.product_1.id,
            'product_uom_qty': 5.0,
            'picking_id': picking.id,
            'rule_id': rule.id,
        })
        pos_move._action_confirm()
        neg_move = pos_move.copy({
            'product_uom_qty': -2.0,
        })
        neg_move._action_confirm()
        self.assertEqual(picking.move_ids.product_uom_qty, 3.0)
