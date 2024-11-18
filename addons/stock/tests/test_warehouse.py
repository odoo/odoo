# -*- coding: utf-8 -*-

from odoo import Command
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests import Form


class TestWarehouse(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Deco Addict'})

    def test_inventory_product(self):
        self.product_1.is_storable = True
        product_1_quant = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_1.id,
            'inventory_quantity': 50.0,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })
        product_1_quant.action_apply_inventory()

        # Make sure the inventory was successful
        move_in_id = self.env['stock.move'].search([('is_inventory', '=', True), ('product_id', '=', self.product_1.id)])
        self.assertEqual(len(move_in_id), 1)
        self.assertEqual(move_in_id.product_qty, 50.0)
        self.assertEqual(product_1_quant.quantity, 50.0)
        self.assertEqual(move_in_id.product_uom, self.product_1.uom_id)
        self.assertEqual(move_in_id.state, 'done')

        # Update the inventory, set to 35
        product_1_quant.inventory_quantity = 35.0
        product_1_quant.action_apply_inventory()

        # Check related move and quants
        move_ids = self.env['stock.move'].search([('is_inventory', '=', True), ('product_id', '=', self.product_1.id)])
        self.assertEqual(len(move_ids), 2)
        move_out_id = move_ids[-1]
        self.assertEqual(move_out_id.product_qty, 15.0)
        self.assertEqual(move_out_id.location_id, self.warehouse_1.lot_stock_id)
        self.assertEqual(move_out_id.location_dest_id, self.product_1.property_stock_inventory)  # Inventory loss
        self.assertEqual(move_out_id.state, 'done')

        quants = self.env['stock.quant']._gather(self.product_1, self.product_1.property_stock_inventory)
        self.assertEqual(len(quants), 1)  # One quant created for inventory loss

        # Check quantity of product in various locations: current, its parent, brother and other
        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.warehouse_1.lot_stock_id).quantity, 35.0)
        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.warehouse_1.lot_stock_id.location_id).quantity, 35.0)
        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.warehouse_1.view_location_id).quantity, 35.0)

        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.warehouse_1.wh_input_stock_loc_id).quantity, 0.0)
        self.assertEqual(self.env['stock.quant']._gather(self.product_1, self.env.ref('stock.stock_location_stock')).quantity, 0.0)

    def test_initial_quant_location(self):
        """
        When updating product quantity, new quant should have its location set
        to the stock location of the top warehouse.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        suppliers_location = self.env.ref('stock.stock_location_suppliers')

        warehouse = self.env['stock.warehouse'].create({
            'name': 'Mixed locations',
            'code': 'TEST',
            'sequence': 0,
        })
        warehouse.in_type_id.default_location_dest_id = suppliers_location
        warehouse.lot_stock_id = stock_location

        quant = self.env['stock.quant'].new({
            'product_id': self.product_1.id,
            'inventory_quantity': 1,
        })
        quant._onchange_product_id()

        self.assertEqual(quant.location_id, stock_location)

    def test_inventory_wizard_as_user(self):
        """ Using the "Update Quantity" wizard as stock user.
        """
        self.product_1.is_storable = True
        InventoryWizard = self.env['stock.change.product.qty'].with_user(self.user_stock_user)
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

    def test_basic_move(self):
        product = self.product_3.with_user(self.user_stock_manager)
        product.is_storable = True
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

        customer_move.quantity = 5
        customer_move.picked = True
        customer_move._action_done()
        self.assertEqual(product.qty_available, -5.0)

        # compensate negative quants by receiving products from supplier
        receive_move = self._create_move(product, self.env.ref('stock.stock_location_suppliers'), self.warehouse_1.lot_stock_id, product_uom_qty=15)

        receive_move._action_confirm()
        receive_move.quantity = 15
        receive_move.picked = True
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

        customer_move_2.quantity = 2.0
        customer_move_2.picked = True
        customer_move_2._action_done()
        product._compute_quantities()
        self.assertEqual(product.qty_available, 8.0)

    def test_inventory_adjustment_and_negative_quants_1(self):
        """Make sure negative quants from returns get wiped out with an inventory adjustment"""
        productA = self.env['product.product'].create({'name': 'Product A', 'is_storable': True})
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
        picking_out.move_ids.quantity = 1
        picking_out.move_ids.picked = True
        picking_out._action_done()

        quant = self.env['stock.quant'].search([('product_id', '=', productA.id), ('location_id', '=', stock_location.id)])
        self.assertEqual(len(quant), 1)
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_out.ids, active_id=picking_out.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_ids.quantity = 1
        return_pick.move_ids.picked = True
        return_pick._action_done()

        quant = self.env['stock.quant'].search([('product_id', '=', productA.id), ('location_id', '=', stock_location.id)])
        self.assertEqual(sum(quant.mapped('quantity')), 0)

    def test_inventory_adjustment_and_negative_quants_2(self):
        """Make sure negative quants get wiped out with an inventory adjustment"""
        productA = self.env['product.product'].create({'name': 'Product A', 'is_storable': True})
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
        picking_out.move_ids.quantity = 1
        picking_out.move_ids.picked = True
        picking_out._action_done()

        # Make an inventory adjustment to set the quantity to 0
        quant = self.env['stock.quant'].search([('product_id', '=', productA.id), ('location_id', '=', stock_location.id)])
        self.assertEqual(len(quant), 1, "Wrong number of quants created.")
        self.assertEqual(quant.quantity, -1, "Theoretical quantity should be -1.")
        # Put the quantity back to 0
        quant.inventory_quantity = 0
        quant.action_apply_inventory()

        # The inventory adjustment should have created one
        move = self.env['stock.move'].search([('product_id', '=', productA.id), ('is_inventory', '=', True)])
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_qty, 1, "Moves created with wrong quantity.")
        self.assertEqual(move.location_id.id, location_loss.id)

        # There should be no quant in the stock location
        self.env['stock.quant']._quant_tasks()
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

        distribution_partner = self.env['res.partner'].create({'name': 'Distribution Center'})
        warehouse_distribution = self.env['stock.warehouse'].create({
            'name': 'Dist.',
            'code': 'DIST',
            'resupply_wh_ids': [(6, 0, [warehouse_stock.id])],
            'partner_id': distribution_partner.id,
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
            'is_storable': True,
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

        self.assertTrue(self.env['stock.picking'].search([('location_id', '=', self.env.company.internal_transit_location_id.id), ('partner_id', '=', distribution_partner.id)]))
        self.assertTrue(self.env['stock.picking'].search([('location_dest_id', '=', self.env.company.internal_transit_location_id.id), ('partner_id', '=', distribution_partner.id)]))

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
            'is_storable': True,
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
            'state': 'draft',
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
        picking_stock_transit.move_ids[0].quantity = 1.0
        picking_stock_transit.move_ids[0].picked = True
        picking_stock_transit._action_done()

        picking_transit_shop_namur = self.env['stock.picking'].search([('location_dest_id', '=', warehouse_shop_namur.lot_stock_id.id)])
        self.assertTrue(picking_transit_shop_namur)
        picking_transit_shop_namur.action_assign()
        picking_transit_shop_namur.move_ids[0].quantity = 1.0
        picking_transit_shop_namur.move_ids[0].picked = True
        picking_transit_shop_namur._action_done()

        picking_out_namur.action_assign()
        picking_out_namur.move_ids[0].picked = True
        picking_out_namur.move_ids[0].quantity = 1.0
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
            'state': 'draft',
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
        picking_stock_transit.move_ids[0].quantity = 1.0
        picking_stock_transit.move_ids[0].picked = True
        picking_stock_transit._action_done()

        picking_transit_shop_wavre = self.env['stock.picking'].search([('location_dest_id', '=', warehouse_shop_wavre.lot_stock_id.id)])
        self.assertTrue(picking_transit_shop_wavre)
        picking_transit_shop_wavre.action_assign()
        picking_transit_shop_wavre.move_ids[0].quantity = 1.0
        picking_transit_shop_wavre.move_ids[0].picked = True
        picking_transit_shop_wavre._action_done()

        picking_out_wavre.action_assign()
        picking_out_wavre.move_ids[0].quantity = 1.0
        picking_out_wavre.move_ids[0].picked = True
        picking_out_wavre._action_done()

        # Check that the correct quantity has been provided to customer
        self.assertEqual(self.env['stock.quant']._gather(product, customer_location).quantity, 2)
        # Ensure there still no quants in distribution warehouse
        self.assertEqual(sum(self.env['stock.quant']._gather(product, warehouse_distribution_wavre.lot_stock_id).mapped('quantity')), 0)

    def test_add_resupply_warehouse_one_by_one(self):
        """ Checks that selecting a warehouse as a resupply warehouse one after another correctly sets the routes as well.
        """
        warehouse_A, warehouse_B, warehouse_C = self.env['stock.warehouse'].create([{
            'name': code,
            'code': code,
        } for code in ['WH_A', 'WH_B', 'WH_C']])
        warehouse_A.resupply_wh_ids = [Command.link(warehouse_B.id)]
        # Assign Warehouse B as supplier warehouse
        self.assertEqual(len(warehouse_A.resupply_route_ids), 1)
        self.assertEqual(warehouse_A.resupply_route_ids.supplier_wh_id, warehouse_B)
        # Assign Warehouse C as supplier warehouse
        warehouse_A.resupply_wh_ids = [Command.link(warehouse_C.id)]
        self.assertEqual(len(warehouse_A.resupply_route_ids), 2)
        self.assertRecordValues(warehouse_A.resupply_route_ids.sorted('id'), [
            {'supplier_wh_id': warehouse_B.id},
            {'supplier_wh_id': warehouse_C.id},
        ])

    def test_toggle_resupply_warehouse(self):
        """ Checks that selecting then unselecting a warehouse as resupply correctly archives/unarchives the related route.
        """
        warehouse_A = self.env['stock.warehouse'].create({
            'name': 'Warehouse A',
            'code': 'WH_A',
        })
        warehouse_B = self.env['stock.warehouse'].create({
            'name': 'Warehouse B',
            'code': 'WH_B',
            'resupply_wh_ids': [Command.set(warehouse_A.ids)],
        })
        resupply_route = warehouse_B.resupply_route_ids
        self.assertTrue(resupply_route.active, 'Route should be active')
        # Un-select Warehouse A as a resupply warehouse
        warehouse_B.resupply_wh_ids = [Command.set([])]
        self.assertFalse(warehouse_B.resupply_route_ids)
        self.assertFalse(resupply_route.active, 'Route should now be inactive')
        # Re-select Warehouse A as a resupply warehouse
        warehouse_B.resupply_wh_ids = [Command.set(warehouse_A.ids)]
        self.assertEqual(warehouse_B.resupply_route_ids, resupply_route)
        self.assertTrue(resupply_route.active, 'Route should now be active')

    def test_muti_step_resupply_warehouse(self):
        """ Simulate the following situation:
        - First warehouse has a 3-steps delivery
        - Second warehouse has a 3-steps reception
        - Second warehouse is resupplied by the first warehouse
        - A product has some stock in the first warehouse
        - A reordering rule is set on the product to fill the second warehouse
        Ensure that the product can move all the way from the first to the second warehouse.
        """
        warehouse_A = self.env['stock.warehouse'].create({
            'name': 'Warehouse A',
            'code': 'WH_A',
            'delivery_steps': 'pick_pack_ship',
        })
        warehouse_B = self.env['stock.warehouse'].create({
            'name': 'Warehouse B',
            'code': 'WH_B',
            'reception_steps': 'three_steps',
            'resupply_wh_ids': [Command.link(warehouse_A.id)],
        })
        self.product_3.write({
            'type': 'consu',
            'is_storable': True,
            'route_ids': [Command.link(warehouse_B.resupply_route_ids.id)],
        })
        self.env['stock.quant']._update_available_quantity(self.product_3, warehouse_A.lot_stock_id, 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_3, warehouse_A.lot_stock_id), 1)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_3, warehouse_B.lot_stock_id), 0)

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'location_id': warehouse_B.lot_stock_id.id,
            'product_id': self.product_3.id,
            'qty_to_order': 1.0,
        })
        orderpoint.action_replenish()
        # Check that the orderpoint generated the source move from the furthest location.
        move = self.env['stock.move'].search([('location_id', '=', warehouse_A.lot_stock_id.id), ('origin', '=', orderpoint.name)])
        self.assertTrue(move, 'No move created from WH_A/Stock')

        # Validate each intermediate transfers towards resupply of WH_B/Stock
        inter_wh_loc = self.env.company.internal_transit_location_id
        step_location_ids = [
            (warehouse_A.lot_stock_id.id, warehouse_A.wh_pack_stock_loc_id.id),             # WH_A/Stock -> WH_A/Packing Zone
            (warehouse_A.wh_pack_stock_loc_id.id, warehouse_A.wh_output_stock_loc_id.id),   # WH_A/Packing Zone -> WH_A/Output
            (warehouse_A.wh_output_stock_loc_id.id, inter_wh_loc.id),                       # WH_A/Output -> Inter-warehouse transit
            (inter_wh_loc.id, warehouse_B.wh_input_stock_loc_id.id),                        # Inter-warehouse transit -> WH_B/Input
            (warehouse_B.wh_input_stock_loc_id.id, warehouse_B.wh_qc_stock_loc_id.id),      # WH_B/Input -> WH_B/Quality Control
            (warehouse_B.wh_qc_stock_loc_id.id, warehouse_B.lot_stock_id.id),               # WH_B/Quality Control -> WH_B/Stock
        ]
        for loc_src_id, loc_dest_id in step_location_ids:
            self.assertEqual(move.location_id.id, loc_src_id)
            self.assertEqual(move.location_dest_id.id, loc_dest_id)
            move.picked = True
            move._action_done()
            self.assertEqual(move.state, 'done')
            move = move.move_dest_ids
        # Verify that the quantity has been properly transfered from WH_A/Stock to WH_B/Stock
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_3, warehouse_A.lot_stock_id), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product_3, warehouse_B.lot_stock_id), 1)

    def test_change_delivery_step_resupply_warehouse(self):
        """ Verifies that when changing the delivery steps of a warehouse, it correctly adds/removes the extra rule
        that is required to resupply the Output location.
        """
        warehouse_A = self.env['stock.warehouse'].create({
            'name': 'Warehouse X',
            'code': 'WH_X',
        })
        warehouse_B = self.env['stock.warehouse'].create({
            'name': 'Warehouse Y',
            'code': 'WH_Y',
            'resupply_wh_ids': [Command.link(warehouse_A.id)],
        })
        resupply_rules = warehouse_B.resupply_route_ids.rule_ids
        self.assertEqual(len(resupply_rules), 2)
        stock_A_to_transit = resupply_rules.filtered(lambda r: r.location_dest_id == self.env.company.internal_transit_location_id)
        self.assertEqual(stock_A_to_transit.location_src_id, warehouse_A.lot_stock_id)

        # Set Warehouse A to 3 steps, a new rule should be created to resupply Output.
        warehouse_A.delivery_steps = 'pick_pack_ship'
        new_resupply_rules = warehouse_B.resupply_route_ids.rule_ids
        self.assertEqual(len(new_resupply_rules), 3)
        self.assertEqual(stock_A_to_transit.location_src_id, warehouse_A.wh_output_stock_loc_id)
        stock_to_output = new_resupply_rules - resupply_rules
        self.assertEqual(stock_to_output.location_src_id, warehouse_A.lot_stock_id)
        self.assertEqual(stock_to_output.location_dest_id, warehouse_A.wh_output_stock_loc_id)

        # Set Warehouse A to 2 steps, no change should have been made.
        warehouse_A.delivery_steps = 'pick_ship'
        self.assertEqual(warehouse_B.resupply_route_ids.rule_ids, new_resupply_rules)
        self.assertEqual(stock_A_to_transit.location_src_id, warehouse_A.wh_output_stock_loc_id)
        self.assertEqual(stock_to_output.location_dest_id, warehouse_A.wh_output_stock_loc_id)

        # Set Warehouse A to 1 step, the rule to resupply Output should be archived.
        warehouse_A.delivery_steps = 'ship_only'
        self.assertEqual(warehouse_B.resupply_route_ids.rule_ids, resupply_rules)
        self.assertEqual(stock_A_to_transit.location_src_id, warehouse_A.lot_stock_id)
        self.assertFalse(stock_to_output.active, "The intermediate rule should have been archived.")

        # Set Warehouse A back to 2 steps, the rule to resupply Output should be unarchived.
        warehouse_A.delivery_steps = 'pick_ship'
        self.assertTrue(stock_to_output.active, "The intermediate rule should have been unarchived.")
        self.assertEqual(warehouse_B.resupply_route_ids.rule_ids, new_resupply_rules, "No new rule should have been created.")

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

        assert len(set(wh.company_id.mapped("id"))) > 1

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
        warehouse.action_archive()
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
        self.assertFalse(warehouse.out_type_id.active)
        self.assertFalse(warehouse.int_type_id.active)
        self.assertFalse(warehouse.pick_type_id.active)
        self.assertFalse(warehouse.pack_type_id.active)

        # Active warehouse
        warehouse.action_unarchive()
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
        self.assertTrue(warehouse.out_type_id.active)
        self.assertTrue(warehouse.int_type_id.active)
        self.assertFalse(warehouse.pick_type_id.active)
        self.assertFalse(warehouse.pack_type_id.active)

    def test_toggle_active_warehouse_2(self):
        # Required for `delivery_steps` to be visible in the view
        self.env.user.groups_id += self.env.ref('stock.group_adv_location')
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

        route = Form(self.env['stock.route'])
        route.name = "Stair"
        route = route.save()

        route.warehouse_ids = [(6, 0, [warehouse.id, self.warehouse_1.id])]

        # Pre archive a location and a route
        warehouse.delivery_route_id.action_archive()
        warehouse.wh_pack_stock_loc_id.action_archive()

        # Archive warehouse
        warehouse.action_archive()
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
        warehouse.action_unarchive()
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
        self.assertEqual(warehouse.int_type_id.barcode, 'CHICINT')
        self.assertEqual(warehouse.int_type_id.sequence_id.prefix, 'chic/INT/')

        wh = Form(warehouse)
        wh.code = 'CH'
        wh.save()
        self.assertEqual(warehouse.int_type_id.barcode, 'CHINT')
        self.assertEqual(warehouse.int_type_id.sequence_id.prefix, 'CH/INT/')

    def test_location_warehouse(self):
        """ Check that the closest warehouse is selected
        in a warehouse within warehouse situation
        """
        wh = self.env.ref("stock.warehouse0")
        test_warehouse = self.warehouse_1
        location = test_warehouse.lot_stock_id
        self.assertEqual(location.warehouse_id, test_warehouse)

        test_warehouse.view_location_id.location_id = wh.lot_stock_id.id
        wh.sequence = 100
        test_warehouse.sequence = 1
        location._compute_warehouse_id()
        self.assertEqual(location.warehouse_id, test_warehouse)

        wh.sequence = 1
        test_warehouse.sequence = 100
        location._compute_warehouse_id()
        self.assertEqual(location.warehouse_id, test_warehouse)

    def test_location_updates_wh(self):
        warehouse_A = self.env['stock.warehouse'].create({
            'name': 'Warehouse X',
            'code': 'WH_X',
            'delivery_steps': 'pick_pack_ship'
        })
        warehouse_B = self.env['stock.warehouse'].create({
            'name': 'Warehouse Y',
            'code': 'WH_Y',
            'delivery_steps': 'pick_pack_ship'
        })
        picking_out = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': warehouse_A.pick_type_id.id,
            'location_id': warehouse_A.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        customer_move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': warehouse_A.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        picking_form = Form(picking_out)
        picking_form.picking_type_id = warehouse_B.pick_type_id
        picking_form.save()
        self.assertEqual(customer_move.warehouse_id, warehouse_B)
        self.assertEqual(picking_out.picking_type_id, warehouse_B.pick_type_id)
        picking_out.button_validate()
        self.assertEqual(customer_move.move_dest_ids.warehouse_id, warehouse_B)
