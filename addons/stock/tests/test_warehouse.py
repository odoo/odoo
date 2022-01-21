# -*- coding: utf-8 -*-

from odoo.addons.stock.tests.common2 import TestStockCommon
from odoo.tests import Form
from odoo.exceptions import AccessError
from odoo.tools import mute_logger


class TestWarehouse(TestStockCommon):

    def setUp(self):
        super(TestWarehouse, self).setUp()
        self.partner = self.env['res.partner'].create({'name': 'Deco Addict'})

    def test_inventory_product(self):
        self.product_1.type = 'product'
        product_1_quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_1.id,
            'inventory_quantity': 50.0,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })
        inventory = self.env['stock.inventory'].with_user(self.user_stock_manager).create({
            'name': 'Starting for product_1',
            'location_ids': [(4, self.warehouse_1.lot_stock_id.id)],
            'product_ids': [(4, self.product_1.id)],
        })
        inventory.action_start()
        # As done in common.py, there is already an inventory line existing
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 50.0)
        self.assertEqual(inventory.line_ids.product_id, self.product_1)
        self.assertEqual(inventory.line_ids.product_uom_id, self.product_1.uom_id)

        # Update the line, set to 35
        inventory.line_ids.write({'product_qty': 35.0})
        inventory.action_validate()

        # Check related move and quants
        self.assertIn(inventory.name, inventory.move_ids.name)
        self.assertEqual(inventory.move_ids.product_qty, 15.0)
        self.assertEqual(inventory.move_ids.location_id, self.warehouse_1.lot_stock_id)
        self.assertEqual(inventory.move_ids.location_dest_id, self.product_1.property_stock_inventory)  # Inventory loss
        self.assertEqual(inventory.move_ids.state, 'done')
        quants = self.env['stock.quant']._gather(self.product_1, self.product_1.property_stock_inventory)
        self.assertEqual(len(quants), 1)  # One quant created for inventory loss

        # Check quantity of product in various locations: current, its parent, brother and other
        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.warehouse_1.lot_stock_id).quantity, 35.0)
        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.warehouse_1.lot_stock_id.location_id).quantity, 35.0)
        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.warehouse_1.view_location_id).quantity, 35.0)

        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.warehouse_1.wh_input_stock_loc_id).quantity, 0.0)
        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.env.ref('stock.stock_location_stock')).quantity, 0.0)

    def test_inventory_wizard_as_manager(self):
        """ Using the "Update Quantity" wizard as stock manager.
        """
        self.product_1.type = 'product'
        InventoryWizard = self.env['stock.change.product.qty'].with_user(self.user_stock_manager)
        inventory_wizard = InventoryWizard.create({
            'product_id': self.product_1.id,
            'product_tmpl_id': self.product_1.product_tmpl_id.id,
            'new_quantity': 50.0,
        })
        inventory_wizard.change_product_qty()
        # Check quantity was updated
        self.assertEqual(self.product_1.virtual_available, 50.0)
        self.assertEqual(self.product_1.qty_available, 50.0)

        # Check associated quants: 2 quants for the product and the quantity (1 in stock, 1 in inventory adjustment)
        quant = self.env['stock.quant'].search([('id', 'not in', self.existing_quants.ids)])
        self.assertEqual(len(quant), 2)

    def test_inventory_wizard_as_user(self):
        """ Using the "Update Quantity" wizard as stock user.
        """
        self.product_1.type = 'product'
        InventoryWizard = self.env['stock.change.product.qty'].with_user(self.user_stock_user)
        inventory_wizard = InventoryWizard.create({
            'product_id': self.product_1.id,
            'product_tmpl_id': self.product_1.product_tmpl_id.id,
            'new_quantity': 50.0,
        })
        # User has no right on quant, must raise an AccessError
        with self.assertRaises(AccessError):
            inventory_wizard.change_product_qty()
        # Check quantity wasn't updated
        self.assertEqual(self.product_1.virtual_available, 0.0)
        self.assertEqual(self.product_1.qty_available, 0.0)

        # Check associated quants: 0 quant expected
        quant = self.env['stock.quant'].search([('id', 'not in', self.existing_quants.ids)])
        self.assertEqual(len(quant), 0)

    def test_basic_move(self):
        product = self.product_3.with_user(self.user_stock_manager)
        product.type = 'product'
        picking_out = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.warehouse_1.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        customer_move = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 5,
            'product_uom': product.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.warehouse_1.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        # simulate create + onchange
        # test move values
        self.assertEqual(customer_move.product_uom, product.uom_id)
        self.assertEqual(customer_move.location_id, self.warehouse_1.lot_stock_id)
        self.assertEqual(customer_move.location_dest_id, self.env.ref('stock.stock_location_customers'))

        # confirm move, check quantity on hand and virtually available, without location context
        customer_move._action_confirm()
        self.assertEqual(product.qty_available, 0.0)
        self.assertEqual(product.virtual_available, -5.0)

        customer_move.quantity_done = 5
        customer_move._action_done()
        self.assertEqual(product.qty_available, -5.0)

        # compensate negative quants by receiving products from supplier
        receive_move = self._create_move(product, self.env.ref('stock.stock_location_suppliers'), self.warehouse_1.lot_stock_id, product_uom_qty=15)

        receive_move._action_confirm()
        receive_move.quantity_done = 15
        receive_move._action_done()

        product._compute_quantities()
        self.assertEqual(product.qty_available, 10.0)
        self.assertEqual(product.virtual_available, 10.0)

        # new move towards customer
        customer_move_2 = self._create_move(product, self.warehouse_1.lot_stock_id, self.env.ref('stock.stock_location_customers'), product_uom_qty=2)

        customer_move_2._action_confirm()
        product._compute_quantities()
        self.assertEqual(product.qty_available, 10.0)
        self.assertEqual(product.virtual_available, 8.0)

        customer_move_2.quantity_done = 2.0
        customer_move_2._action_done()
        product._compute_quantities()
        self.assertEqual(product.qty_available, 8.0)

    def test_inventory_adjustment_and_negative_quants_1(self):
        """Make sure negative quants from returns get wiped out with an inventory adjustment"""
        productA = self.env['product.product'].create({'name': 'Product A', 'type': 'product'})
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')

        # Create a picking out and force availability
        picking_out = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
        })
        self.env['stock.move'].create({
            'name': productA.name,
            'product_id': productA.id,
            'product_uom_qty': 1,
            'product_uom': productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
        })
        picking_out.action_confirm()
        picking_out.move_lines.quantity_done = 1
        picking_out._action_done()

        quant = self.env['stock.quant'].search([('product_id', '=', productA.id), ('location_id', '=', stock_location.id)])
        self.assertEqual(len(quant), 1)
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_out.ids, active_id=picking_out.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_lines.quantity_done = 1
        return_pick._action_done()

        quant = self.env['stock.quant'].search([('product_id', '=', productA.id), ('location_id', '=', stock_location.id)])
        self.assertEqual(sum(quant.mapped('quantity')), 0)

    def test_inventory_adjustment_and_negative_quants_2(self):
        """Make sure negative quants get wiped out with an inventory adjustment"""
        productA = self.env['product.product'].create({'name': 'Product A', 'type': 'product'})
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')
        location_loss = productA.property_stock_inventory

        # Create a picking out and force availability
        picking_out = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
        })
        self.env['stock.move'].create({
            'name': productA.name,
            'product_id': productA.id,
            'product_uom_qty': 1,
            'product_uom': productA.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
        })
        picking_out.action_confirm()
        picking_out.move_lines.quantity_done = 1
        picking_out._action_done()

        # Make an inventory adjustment to set the quantity to 0
        inventory = self.env['stock.inventory'].create({
            'name': 'Starting for product_1',
            'location_ids': [(4, stock_location.id)],
            'product_ids': [(4, productA.id)],
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1, "Wrong inventory lines generated.")
        self.assertEqual(inventory.line_ids.theoretical_qty, -1, "Theoretical quantity should be -1.")
        inventory.line_ids.product_qty = 0  # Put the quantity back to 0
        inventory.action_validate()

        # The inventory adjustment should have created one
        self.assertEqual(len(inventory.move_ids), 1)
        quantity = inventory.move_ids.mapped('product_qty')
        self.assertEqual(quantity, [1], "Moves created with wrong quantity.")
        location_ids = inventory.move_ids.mapped('location_id').ids
        self.assertEqual(set(location_ids), {location_loss.id})

        # There should be no quant in the stock location
        quants = self.env['stock.quant'].search([('product_id', '=', productA.id), ('location_id', '=', stock_location.id)])
        self.assertEqual(sum(quants.mapped('quantity')), 0)

        # There should be one quant in the inventory loss location
        quant = self.env['stock.quant'].search([('product_id', '=', productA.id), ('location_id', '=', location_loss.id)])
        self.assertEqual(len(quant), 1)

    def test_resupply_route(self):
        """ Simulate a resupply chain between warehouses.
        Stock -> transit -> Dist. -> transit -> Shop -> Customer
        Create the move from Shop to Customer and ensure that all the pull
        rules are triggered in order to complete the move chain to Stock.
        """
        warehouse_stock = self.env['stock.warehouse'].create({
            'name': 'Stock.',
            'code': 'STK',
        })

        warehouse_distribution = self.env['stock.warehouse'].create({
            'name': 'Dist.',
            'code': 'DIST',
            'resupply_wh_ids': [(6, 0, [warehouse_stock.id])]
        })

        warehouse_shop = self.env['stock.warehouse'].create({
            'name': 'Shop',
            'code': 'SHOP',
            'resupply_wh_ids': [(6, 0, [warehouse_distribution.id])]
        })

        route_stock_to_dist = warehouse_distribution.resupply_route_ids
        route_dist_to_shop = warehouse_shop.resupply_route_ids

        # Change the procure_method on the pull rules between dist and shop
        # warehouses. Since mto and resupply routes are both on product it will
        # select one randomly between them and if it select the resupply it is
        # 'make to stock' and it will not create the picking between stock and
        # dist warehouses.
        route_dist_to_shop.rule_ids.write({'procure_method': 'make_to_order'})

        product = self.env['product.product'].create({
            'name': 'Fakir',
            'type': 'product',
            'route_ids': [(4, route_id) for route_id in [route_stock_to_dist.id, route_dist_to_shop.id, self.env.ref('stock.route_warehouse0_mto').id]],
        })

        picking_out = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': warehouse_shop.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': warehouse_shop.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'warehouse_id': warehouse_shop.id,
            'procure_method': 'make_to_order',
        })
        picking_out.action_confirm()

        moves = self.env['stock.move'].search([('product_id', '=', product.id)])
        # Shop/Stock -> Customer
        # Transit -> Shop/Stock
        # Dist/Stock -> Transit
        # Transit -> Dist/Stock
        # Stock/Stock -> Transit
        self.assertEqual(len(moves), 5, 'Invalid moves number.')
        self.assertTrue(self.env['stock.move'].search([('location_id', '=', warehouse_stock.lot_stock_id.id)]))
        self.assertTrue(self.env['stock.move'].search([('location_dest_id', '=', warehouse_distribution.lot_stock_id.id)]))
        self.assertTrue(self.env['stock.move'].search([('location_id', '=', warehouse_distribution.lot_stock_id.id)]))
        self.assertTrue(self.env['stock.move'].search([('location_dest_id', '=', warehouse_shop.lot_stock_id.id)]))
        self.assertTrue(self.env['stock.move'].search([('location_id', '=', warehouse_shop.lot_stock_id.id)]))

    def test_mutiple_resupply_warehouse(self):
        """ Simulate the following situation:
        - 2 shops with stock are resupply by 2 distinct warehouses
        - Shop Namur is resupply by the warehouse stock Namur
        - Shop Wavre is resupply by the warehouse stock Wavre
        - Simulate 2 moves for the same product but in different shop.
        This test ensure that the move are supplied by the correct distribution
        warehouse.
        """
        customer_location = self.env.ref('stock.stock_location_customers')

        warehouse_distribution_wavre = self.env['stock.warehouse'].create({
            'name': 'Stock Wavre.',
            'code': 'WV',
        })

        warehouse_shop_wavre = self.env['stock.warehouse'].create({
            'name': 'Shop Wavre',
            'code': 'SHWV',
            'resupply_wh_ids': [(6, 0, [warehouse_distribution_wavre.id])]
        })

        warehouse_distribution_namur = self.env['stock.warehouse'].create({
            'name': 'Stock Namur.',
            'code': 'NM',
        })

        warehouse_shop_namur = self.env['stock.warehouse'].create({
            'name': 'Shop Namur',
            'code': 'SHNM',
            'resupply_wh_ids': [(6, 0, [warehouse_distribution_namur.id])]
        })

        route_shop_namur = warehouse_shop_namur.resupply_route_ids
        route_shop_wavre = warehouse_shop_wavre.resupply_route_ids
        # The product contains the 2 resupply routes.
        product = self.env['product.product'].create({
            'name': 'Fakir',
            'type': 'product',
            'route_ids': [(4, route_id) for route_id in [route_shop_namur.id, route_shop_wavre.id, self.env.ref('stock.route_warehouse0_mto').id]],
        })

        # Add 1 quant in each distribution warehouse.
        self.env['stock.quant']._update_available_quantity(product, warehouse_distribution_wavre.lot_stock_id, 1.0)
        self.env['stock.quant']._update_available_quantity(product, warehouse_distribution_namur.lot_stock_id, 1.0)

        # Create the move for the shop Namur. Should create a resupply from
        # distribution warehouse Namur.
        picking_out_namur = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': warehouse_shop_namur.lot_stock_id.id,
            'location_dest_id': customer_location.id,
        })
        self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'picking_id': picking_out_namur.id,
            'location_id': warehouse_shop_namur.lot_stock_id.id,
            'location_dest_id': customer_location.id,
            'warehouse_id': warehouse_shop_namur.id,
            'procure_method': 'make_to_order',
        })
        picking_out_namur.action_confirm()

        # Validate the picking
        # Dist. warehouse Namur -> transit Location -> Shop Namur
        picking_stock_transit = self.env['stock.picking'].search([('location_id', '=', warehouse_distribution_namur.lot_stock_id.id)])
        self.assertTrue(picking_stock_transit)
        picking_stock_transit.action_assign()
        picking_stock_transit.move_lines[0].quantity_done = 1.0
        picking_stock_transit._action_done()

        picking_transit_shop_namur = self.env['stock.picking'].search([('location_dest_id', '=', warehouse_shop_namur.lot_stock_id.id)])
        self.assertTrue(picking_transit_shop_namur)
        picking_transit_shop_namur.action_assign()
        picking_transit_shop_namur.move_lines[0].quantity_done = 1.0
        picking_transit_shop_namur._action_done()

        picking_out_namur.action_assign()
        picking_out_namur.move_lines[0].quantity_done = 1.0
        picking_out_namur._action_done()

        # Check that the correct quantity has been provided to customer
        self.assertEqual(self.env['stock.quant']._gather(product, customer_location).quantity, 1)
        # Ensure there still no quants in distribution warehouse
        self.assertEqual(sum(self.env['stock.quant']._gather(product, warehouse_distribution_namur.lot_stock_id).mapped('quantity')), 0)

        # Create the move for the shop Wavre. Should create a resupply from
        # distribution warehouse Wavre.
        picking_out_wavre = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': warehouse_shop_wavre.lot_stock_id.id,
            'location_dest_id': customer_location.id,
        })
        self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'picking_id': picking_out_wavre.id,
            'location_id': warehouse_shop_wavre.lot_stock_id.id,
            'location_dest_id': customer_location.id,
            'warehouse_id': warehouse_shop_wavre.id,
            'procure_method': 'make_to_order',
        })
        picking_out_wavre.action_confirm()

        # Validate the picking
        # Dist. warehouse Wavre -> transit Location -> Shop Wavre
        picking_stock_transit = self.env['stock.picking'].search([('location_id', '=', warehouse_distribution_wavre.lot_stock_id.id)])
        self.assertTrue(picking_stock_transit)
        picking_stock_transit.action_assign()
        picking_stock_transit.move_lines[0].quantity_done = 1.0
        picking_stock_transit._action_done()

        picking_transit_shop_wavre = self.env['stock.picking'].search([('location_dest_id', '=', warehouse_shop_wavre.lot_stock_id.id)])
        self.assertTrue(picking_transit_shop_wavre)
        picking_transit_shop_wavre.action_assign()
        picking_transit_shop_wavre.move_lines[0].quantity_done = 1.0
        picking_transit_shop_wavre._action_done()

        picking_out_wavre.action_assign()
        picking_out_wavre.move_lines[0].quantity_done = 1.0
        picking_out_wavre._action_done()

        # Check that the correct quantity has been provided to customer
        self.assertEqual(self.env['stock.quant']._gather(product, customer_location).quantity, 2)
        # Ensure there still no quants in distribution warehouse
        self.assertEqual(sum(self.env['stock.quant']._gather(product, warehouse_distribution_wavre.lot_stock_id).mapped('quantity')), 0)

    def test_noleak(self):
        # non-regression test to avoid company_id leaking to other warehouses (see blame)
        partner = self.env['res.partner'].create({'name': 'Chicago partner'})
        company = self.env['res.company'].create({
            'name': 'My Company (Chicago)1',
            'currency_id': self.ref('base.USD')
        })
        self.env['stock.warehouse'].create({
            'name': 'Chicago Warehouse2',
            'company_id': company.id,
            'code': 'Chic2',
            'partner_id': partner.id
        })
        wh = self.env["stock.warehouse"].search([])

        assert len(set(wh.mapped("company_id.id"))) > 1

        companies_before = wh.mapped(lambda w: (w.id, w.company_id))
        # writing on any field should change the company of warehouses
        wh.write({"name": "whatever"})
        companies_after = wh.mapped(lambda w: (w.id, w.company_id))

        self.assertEqual(companies_after, companies_before)

    def test_toggle_active_warehouse_1(self):
        """ Basic test that create a warehouse with classic configuration.
        Archive it and check that locations, picking types, routes, rules are
        correclty active or archive.
        """
        wh = Form(self.env['stock.warehouse'])
        wh.name = "The attic of Willy"
        wh.code = "WIL"
        warehouse = wh.save()

        custom_location = Form(self.env['stock.location'])
        custom_location.name = "A Trunk"
        custom_location.location_id = warehouse.lot_stock_id
        custom_location = custom_location.save()

        # Archive warehouse
        warehouse.toggle_active()
        # Global rule
        self.assertFalse(warehouse.mto_pull_id.active)

        # Route
        self.assertFalse(warehouse.reception_route_id.active)
        self.assertFalse(warehouse.delivery_route_id.active)

        # Location
        self.assertFalse(warehouse.lot_stock_id.active)
        self.assertFalse(warehouse.wh_input_stock_loc_id.active)
        self.assertFalse(warehouse.wh_qc_stock_loc_id.active)
        self.assertFalse(warehouse.wh_output_stock_loc_id.active)
        self.assertFalse(warehouse.wh_pack_stock_loc_id.active)
        self.assertFalse(custom_location.active)

        # Picking Type
        self.assertFalse(warehouse.in_type_id.active)
        self.assertFalse(warehouse.in_type_id.show_operations)
        self.assertFalse(warehouse.out_type_id.active)
        self.assertFalse(warehouse.int_type_id.active)
        self.assertFalse(warehouse.pick_type_id.active)
        self.assertFalse(warehouse.pack_type_id.active)

        # Active warehouse
        warehouse.toggle_active()
        # Global rule
        self.assertTrue(warehouse.mto_pull_id.active)

        # Route
        self.assertTrue(warehouse.reception_route_id.active)
        self.assertTrue(warehouse.delivery_route_id.active)

        # Location
        self.assertTrue(warehouse.lot_stock_id.active)
        self.assertFalse(warehouse.wh_input_stock_loc_id.active)
        self.assertFalse(warehouse.wh_qc_stock_loc_id.active)
        self.assertFalse(warehouse.wh_output_stock_loc_id.active)
        self.assertFalse(warehouse.wh_pack_stock_loc_id.active)
        self.assertTrue(custom_location.active)

        # Picking Type
        self.assertTrue(warehouse.in_type_id.active)
        self.assertFalse(warehouse.in_type_id.show_operations)
        self.assertTrue(warehouse.out_type_id.active)
        self.assertTrue(warehouse.int_type_id.active)
        self.assertFalse(warehouse.pick_type_id.active)
        self.assertFalse(warehouse.pack_type_id.active)

    def test_toggle_active_warehouse_2(self):
        wh = Form(self.env['stock.warehouse'])
        wh.name = "The attic of Willy"
        wh.code = "WIL"
        wh.reception_steps = "two_steps"
        wh.delivery_steps = "pick_pack_ship"
        warehouse = wh.save()

        warehouse.resupply_wh_ids = [(6, 0, [self.warehouse_1.id])]

        custom_location = Form(self.env['stock.location'])
        custom_location.name = "A Trunk"
        custom_location.location_id = warehouse.lot_stock_id
        custom_location = custom_location.save()

        # Add a warehouse on the route.
        warehouse.reception_route_id.write({
            'warehouse_ids': [(4, self.warehouse_1.id)]
        })

        route = Form(self.env['stock.location.route'])
        route.name = "Stair"
        route = route.save()

        route.warehouse_ids = [(6, 0, [warehouse.id, self.warehouse_1.id])]

        # Pre archive a location and a route
        warehouse.delivery_route_id.toggle_active()
        warehouse.wh_pack_stock_loc_id.toggle_active()

        # Archive warehouse
        warehouse.toggle_active()
        # Global rule
        self.assertFalse(warehouse.mto_pull_id.active)

        # Route
        self.assertTrue(warehouse.reception_route_id.active)
        self.assertFalse(warehouse.delivery_route_id.active)
        self.assertTrue(route.active)

        # Location
        self.assertFalse(warehouse.lot_stock_id.active)
        self.assertFalse(warehouse.wh_input_stock_loc_id.active)
        self.assertFalse(warehouse.wh_qc_stock_loc_id.active)
        self.assertFalse(warehouse.wh_output_stock_loc_id.active)
        self.assertFalse(warehouse.wh_pack_stock_loc_id.active)
        self.assertFalse(custom_location.active)

        # Picking Type
        self.assertFalse(warehouse.in_type_id.active)
        self.assertFalse(warehouse.out_type_id.active)
        self.assertFalse(warehouse.int_type_id.active)
        self.assertFalse(warehouse.pick_type_id.active)
        self.assertFalse(warehouse.pack_type_id.active)

        # Active warehouse
        warehouse.toggle_active()
        # Global rule
        self.assertTrue(warehouse.mto_pull_id.active)

        # Route
        self.assertTrue(warehouse.reception_route_id.active)
        self.assertTrue(warehouse.delivery_route_id.active)

        # Location
        self.assertTrue(warehouse.lot_stock_id.active)
        self.assertTrue(warehouse.wh_input_stock_loc_id.active)
        self.assertFalse(warehouse.wh_qc_stock_loc_id.active)
        self.assertTrue(warehouse.wh_output_stock_loc_id.active)
        self.assertTrue(warehouse.wh_pack_stock_loc_id.active)
        self.assertTrue(custom_location.active)

        # Picking Type
        self.assertTrue(warehouse.in_type_id.active)
        self.assertTrue(warehouse.out_type_id.active)
        self.assertTrue(warehouse.int_type_id.active)
        self.assertTrue(warehouse.pick_type_id.active)
        self.assertTrue(warehouse.pack_type_id.active)

    def test_edit_warehouse_1(self):
        wh = Form(self.env['stock.warehouse'])
        wh.name = "Chicago"
        wh.code = "chic"
        warehouse = wh.save()
        self.assertEqual(warehouse.int_type_id.barcode, 'CHIC-INTERNAL')
        self.assertEqual(warehouse.int_type_id.sequence_id.prefix, 'chic/INT/')

        wh = Form(warehouse)
        wh.code = 'CH'
        wh.save()
        self.assertEqual(warehouse.int_type_id.barcode, 'CH-INTERNAL')
        self.assertEqual(warehouse.int_type_id.sequence_id.prefix, 'CH/INT/')
