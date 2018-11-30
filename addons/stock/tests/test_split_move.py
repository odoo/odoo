# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock.tests.common import TestStockCommon


class TestSplitMove(TestStockCommon):

    def setUp(self):
        super(TestSplitMove, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)

    def test_split_mto_mts_00(self):
        """ Internal Transfer of Product in MTO:
        - Create 2 internal Locations -> Destination Location and Source Location.
        - Create a route - Internal Transfers and add a rule - Internal Source Location -> Internal Destination Location.
        - Add this route to the product.
        - Create an Internal Transfer(Picking 1) for 10 units from Destination Location -> Stock.
        - In the Origin move (Picking 2), change quantity from 10 to 8 and transfer products.
        - In the Picking 1, split the stock move into two, one of 8 in MTO, one of 2 in MTS.
        - Update quants and products should be reserved in the Picking 1, then mark as done.
        This test ensure that when initial demand is decreased, the initial demand in destination move should be splitted into two -> one in   MTO and one in MTS.
        """
        destination_location = self.env['stock.location'].create({
            'location_id': self.stock_location.location_id.id,
            'name': 'Destination Location',
        })
        source_location = self.env['stock.location'].create({
            'location_id': self.stock_location.location_id.id,
            'name': 'Source Location',
        })
        procurement_group = self.env['procurement.group'].create({'name': 'xyz'})

        # Create a route and add rule - Internal Source Location -> Internal Destination Location
        route = self.env['stock.location.route'].create({
            'name': 'Internal Transfers',
            'sequence': 1,
            'product_selectable': True,
            'warehouse_ids': [(4, self.stock_warehouse.id)],
            'rule_ids': [(0, 0, {
                'name': 'Internal Source Location -> Internal Destination Location rule',
                'location_src_id': source_location.id,
                'location_id': destination_location.id,
                'company_id': self.env.user.company_id.id,
                'action': 'pull',
                'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                'procure_method': 'make_to_stock',
                'warehouse_id': self.stock_warehouse.id,
            })],
        })
        # Add this route to product
        product = self.env.ref('product.product_product_3')
        product.write({
             'route_ids': [(4, route.id)]})

        # Create an Internal Transfer from Destination Location - Stock
        picking_1 = self.PickingObj.create({
            'location_id': destination_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.ref('stock.picking_type_internal'),
            'group_id': procurement_group.id,
        })
        move1 = self.MoveObj.create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 10,
            'product_uom': product.uom_id.id,
            'picking_id': picking_1.id,
            'location_id': destination_location.id,
            'location_dest_id': self.stock_location.id,
            'procure_method': 'make_to_order',
            'group_id': procurement_group.id,
        })
        # Confirm Internal Transfer.
        picking_1.action_confirm()
        # Check that the origin move is correctly set
        orig_move = picking_1.move_lines.move_orig_ids
        self.assertEqual(orig_move.location_dest_id.id, destination_location.id, 'Wrong destination location.')

        # find newly created picking
        picking_2 = self.PickingObj.search([('group_id', '=', procurement_group.id), ('location_dest_id', '=', destination_location.id)])
        # check that move1 is the destination move of the move in picking 2
        self.assertEqual(picking_2.move_lines.move_dest_ids, move1, 'Wrong move line in destination move.')
        picking_2.action_confirm()

        # ----------------------------------------------------------------------
        # Decrease the Initial demand
        # ----------------------------------------------------------------------
        #   Product ( 10 Unit ) --> Product ( 8 Unit )
        # ----------------------------------------------------------------------
        for line in picking_2.move_lines:
            # Initial demand should be 10
            self.assertEqual(line.product_uom_qty, 10.0, 'Wrong product quantity.')
            line.write({'product_uom_qty': 8.0})

        # make some quants
        self.StockQuantObj._update_available_quantity(product, source_location, 8.0)
        picking_2.action_assign()
        for line in picking_2.move_lines:
            line.write({'quantity_done': 8.0})
        picking_2.action_done()
        self.assertEqual(picking_2.state, 'done', 'Picking should be in done state.')

        # ======================================================================
        # Before splitting move:
        # ----------------------
        #   Product ( 10 Unit ) - MTO
        #
        # After splitting move:
        # ---------------------
        #   Product (  8 unit ) - MTO
        #   ---------------------------
        #   Product (  2 unit ) - MTS
        # ======================================================================

        # Check that new line of MTS is created for remaining product in Picking 1
        self.assertEqual(len(picking_1.move_ids_without_package), 2, 'New move line of MTS must be created.')
        self.assertEqual(picking_1.move_lines[1].procure_method, 'make_to_stock', 'New move line must be - Make to Stock.')
        self.assertEqual(picking_1.move_lines[1].product_uom_qty, 2.0, 'Wrong product quantity.')

        # Make some quants
        self.StockQuantObj._update_available_quantity(product, destination_location, 2.0)
        picking_1.action_assign()
        self.assertEqual(picking_1.state, 'assigned', 'products must be assigned to the picking.')
        # Validate Picking 1
        res_dict_2 = picking_1.button_validate()
        wizard_2 = self.env[(res_dict_2.get('res_model'))].browse(res_dict_2.get('res_id'))
        wizard_2.process()
        self.assertEqual(picking_1.state, 'done', 'Picking should be in done state.')

    def test_split_mto_mts_01(self):
        """ Deliver in 2 step of Product in MTO:
        - Create a Output Location.
        - Create a route - Deliver in 2 Steps and add 2 rules:
                1) Stock -> Output rule (MTS)
                2) Output -> Customer rule (MTO).
        - Add this route to the product.
        - Create a Picking 1(SHIP) for 10 units from Output -> Customer.
        - In the Picking 2 (PICK), change quantity from 10 to 5 and transfer products from Stock -> Output.
        - In the Picking 1, split the stock move into two, one of 5 in MTO, one of 5 in MTS.
        - Update quants and products should be reserved in the Picking 1, then mark as done.
        This test ensure that when initial demand is decreased, the initial demand in destination move should be splitted into two -> one in   MTO and one in MTS.
        """
        output_location = self.env['stock.location'].create({
            'location_id': self.stock_location.location_id.id,
            'name': 'location',
        })
        procurement_group = self.env['procurement.group'].create({'name': 'abc'})
        # Create rule from Stock -> Output (MTS)
        vals1 = {
                'name': 'Stock -> Output rule',
                'action': 'pull',
                'picking_type_id': self.ref('stock.picking_type_internal'),
                'location_src_id': self.stock_location.id,
                'location_id': output_location.id,
                'procure_method': 'make_to_stock',
                'warehouse_id': self.stock_warehouse.id,
        }
        # Create rule from Output -> Customer (MTO)
        vals2 = {
                'name': 'Output -> Customer rule',
                'action': 'pull',
                'picking_type_id': self.picking_type_out,
                'location_src_id': output_location.id,
                'location_id': self.customer_location,
                'procure_method': 'make_to_order',
                'warehouse_id': self.stock_warehouse.id,
        }
        # Create route and add rules to it
        route = self.env['stock.location.route'].create({
            'name': 'Deliver in 2 steps',
            'sequence': 2,
            'product_selectable': True,
            'warehouse_ids': [(4, self.stock_warehouse.id)],
            'rule_ids': [(0, 0, vals1), (0, 0, vals2)],
        })
        # Add route in product
        self.env.ref('product.product_product_3').write({
             'route_ids': [(4, route.id)]})
        product = self.env.ref('product.product_product_3')

        # Create a Ship (picking_1) from Output -> Customer location
        picking_1 = self.PickingObj.create({
            'location_id': output_location.id,
            'location_dest_id': self.customer_location,
            'partner_id': self.partner_agrolite_id,
            'picking_type_id': self.picking_type_out,
            'group_id': procurement_group.id,
        })
        move1 = self.MoveObj.create({
            'name': 'Delivery order for procurement',
            'product_id': product.id,
            'product_uom_qty': 10,
            'product_uom': product.uom_id.id,
            'picking_id': picking_1.id,
            'location_id': output_location.id,
            'location_dest_id': self.customer_location,
            'procure_method': 'make_to_order',
            'group_id': procurement_group.id,
        })
        # Confirm picking_1
        picking_1.action_confirm()
        orig_move = picking_1.move_lines.move_orig_ids
        self.assertEqual(orig_move.location_dest_id.id, output_location.id, 'Wrong destination location.')

        # find newly created picking - Pick (picking_2)
        picking_2 = self.PickingObj.search([
            ('group_id', '=', procurement_group.id),
            ('location_dest_id', '=', output_location.id),
        ])
        # check that move1 is the destination move of the move in picking_2
        self.assertEqual(picking_2.move_lines.move_dest_ids, move1, 'Wrong move line in destination move.')
        picking_2.action_confirm()

        # ----------------------------------------------------------------------
        # Decrease the Initial demand
        # ----------------------------------------------------------------------
        #   Product ( 10 Unit ) --> Product ( 5 Unit )
        # ----------------------------------------------------------------------
        for line in picking_2.move_lines:
            # Initial demand should be 10
            self.assertEqual(line.product_uom_qty, 10.0, 'Wrong product quantity in picking 2.')
            line.write({'product_uom_qty': 5.0})

        # make some quants
        self.StockQuantObj._update_available_quantity(product, self.stock_location, 5.0)
        picking_2.action_assign()
        for line in picking_2.move_lines:
            line.write({'quantity_done': 5.0})
        picking_2.action_done()
        self.assertEqual(picking_2.state, 'done', 'Picking 2 should be in done state.')

        # ======================================================================
        # Before splitting move:
        # ----------------------
        #   Product ( 10 Unit ) - MTO
        #
        # After splitting move:
        # ---------------------
        #   Product (  5 unit ) - MTO
        #   ---------------------------
        #   Product (  5 unit ) - MTS
        # ======================================================================

        # Check that new line of MTS is created for remaining product in Ship.
        self.assertEqual(len(picking_1.move_ids_without_package), 2, 'New move line of MTS must be created.')
        self.assertEqual(picking_1.move_lines[1].procure_method, 'make_to_stock', 'New move line must be - Make to Stock.')
        self.assertEqual(picking_1.move_lines[1].product_uom_qty, 5.0, 'Wrong product quantity.')

        self.StockQuantObj._update_available_quantity(product, output_location, 5.0)
        picking_1.action_assign()
        self.assertEqual(picking_1.state, 'assigned', 'products must be assigned to the picking.')
        # Validate Ship
        res_dict_2 = picking_1.button_validate()
        wizard_2 = self.env[(res_dict_2.get('res_model'))].browse(res_dict_2.get('res_id'))
        wizard_2.process()
        self.assertEqual(picking_1.state, 'done', 'Picking should be in done state.')
