# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from freezegun import freeze_time
from json import loads

from odoo.fields import Command
from odoo.tests import Form, TransactionCase
from odoo.tools import mute_logger
from odoo.exceptions import UserError


class TestProcRule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product = cls.env['product.product'].create({
            'name': 'Desk Combination',
            'type': 'consu',
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Partner'})

    def test_qty_to_order_remainder_decimal(self):
        """Test case for when remainder is decimal"""
        self.env.user.group_ids += self.env.ref('stock.group_stock_multi_locations')
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = self.product
        orderpoint_form.location_id = self.env.ref('stock.stock_location_stock')
        orderpoint_form.product_min_qty = 4.0
        orderpoint_form.product_max_qty = 5.1
        orderpoint_form.replenishment_uom_id = self.env['uom.uom'].create({
            'name': 'Test UoM',
            'relative_factor': 0.1,
            'relative_uom_id': self.uom_unit.id,
        })
        orderpoint = orderpoint_form.save()
        self.assertAlmostEqual(orderpoint.qty_to_order, orderpoint.product_max_qty)

    def test_endless_loop_rules_from_location(self):
        """ Creates and configure a rule the way, when trying to get rules from
        location, it goes in a state where the found rule tries to trigger another
        rule but finds nothing else than itself and so get stuck in a recursion error."""
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        reception_route = warehouse.reception_route_id
        self.product.is_storable = True

        # Creates a delivery for this product, that way, this product will be to resupply.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = warehouse.out_type_id
        with picking_form.move_ids.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 10
        delivery = picking_form.save()
        delivery.action_confirm()
        self.product._compute_quantities()  # Computes `outgoing_qty` to have the orderpoint.

        # Then, creates a rule and adds it into the route's rules.
        reception_route.rule_ids.action_archive()
        self.env['stock.rule'].create({
            'name': 'Looping Rule',
            'route_id': reception_route.id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'location_src_id': warehouse.lot_stock_id.id,
            'action': 'pull_push',
            'procure_method': 'make_to_order',
            'picking_type_id': warehouse.int_type_id.id,
        })

        # Tries to open the Replenishment view -> It should raise an UserError.
        with self.assertRaises(UserError):
            self.env['stock.warehouse.orderpoint'].action_open_orderpoints()

    def test_proc_rule(self):
        # Create a product route containing a stock rule that will
        # generate a move from Stock for every procurement created in Output
        product_route = self.env['stock.route'].create({
            'name': 'Stock -> output route',
            'product_selectable': True,
            'rule_ids': [(0, 0, {
                'name': 'Stock -> output rule',
                'action': 'pull',
                'picking_type_id': self.ref('stock.picking_type_internal'),
                'location_src_id': self.ref('stock.stock_location_stock'),
                'location_dest_id': self.ref('stock.stock_location_output'),
                'location_dest_from_rule': True,
            })],
        })

        # Set this route on `product.product_product_3`
        self.product.write({
            'route_ids': [(4, product_route.id)]})

        # Create Delivery Order of 10 `product.product_product_3` from Output -> Customer
        product = self.product
        vals = {
            'name': 'Delivery order for procurement',
            'partner_id': self.partner.id,
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.ref('stock.stock_location_output'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_ids': [(0, 0, {
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': 10.00,
                'procure_method': 'make_to_order',
                'location_id': self.ref('stock.stock_location_output'),
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
            'state': 'draft',
        }
        pick_output = self.env['stock.picking'].create(vals)

        # Confirm delivery order.
        pick_output.action_confirm()

        # I run the scheduler.
        # Note: If purchase if already installed, the method _run_buy will be called due
        # to the purchase demo data. As we update the stock module to run this test, the
        # method won't be an attribute of stock.procurement at this moment. For that reason
        # we mute the logger when running the scheduler.
        with mute_logger('odoo.addons.stock.models.procurement'):
            self.env['stock.rule'].run_scheduler()

        # Check that a picking was created from stock to output.
        moves = self.env['stock.move'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', self.ref('stock.stock_location_stock')),
            ('location_dest_id', '=', self.ref('stock.stock_location_output')),
            ('move_dest_ids', 'in', [pick_output.move_ids[0].id])
        ])
        self.assertEqual(len(moves.ids), 1, "It should have created a picking from Stock to Output with the original picking as destination")

    def test_get_rule_respects_sequence_order(self):
        """Test that _get_rule selects the rule associated with the route of the lowest sequence."""

        # Create a warehouse and a product
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        product = self.env['product.product'].create({'name': 'Test Product', 'is_storable': True})

        # Create routes with different sequences to simulate prioritization.
        route_low_priority = self.env['stock.route'].create({'name': 'Route 1', 'sequence': 10})
        rule_low_priority = self.env['stock.rule'].create({
            'name': 'Rule for Route 1',
            'route_id': route_low_priority.id,
            'action': 'pull',
            'location_src_id': warehouse.lot_stock_id.id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'picking_type_id': warehouse.out_type_id.id,
            'sequence': 20,
        })

        # Create a second route with higher priority (lower sequence).
        route_high_priority = self.env['stock.route'].create({'name': 'Route 2', 'sequence': 5})
        rule_high_priority = self.env['stock.rule'].create({
            'name': 'Rule for Route 2',
            'route_id': route_high_priority.id,
            'action': 'pull',
            'location_src_id': warehouse.lot_stock_id.id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'picking_type_id': warehouse.out_type_id.id,
            'sequence': 20,
        })

        # Assign both routes to the product. This order is set so that the method
        # will be forced to sort the routes by their sequence.
        product.write({'route_ids': [(4, route_low_priority.id), (4, route_high_priority.id)]})

        # Call the _get_rule method to simulate rule selection.
        rule = self.env['stock.rule']._get_rule(
            product_id=product,
            location_id=warehouse.lot_stock_id,
            values={
                'warehouse_id': warehouse,
                'route_ids': product.route_ids,
            }
        )

        # Assert that the selected rule corresponds to the route with the lowest sequence.
        self.assertEqual(rule, rule_high_priority,
                         "The rule associated with the route having the lowest sequence "
                         "(high_priority) should be selected.")

    def test_propagate_deadline_move(self):
        deadline = datetime.now()
        move_dest = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'date_deadline': deadline,
            'location_id': self.ref('stock.stock_location_output'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })

        move_orig = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'date_deadline': deadline,
            'move_dest_ids': [(4, move_dest.id)],
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            'quantity': 10,
            'picked': True
        })
        new_deadline = move_orig.date_deadline - timedelta(days=6)
        move_orig.date_deadline = new_deadline
        self.assertEqual(move_dest.date_deadline, new_deadline, msg='deadline date should be propagated')
        move_orig._action_done()
        self.assertAlmostEqual(move_orig.date, datetime.now(), delta=timedelta(seconds=10), msg='date should be now')
        self.assertEqual(move_orig.date_deadline, new_deadline, msg='deadline date should be unchanged')
        self.assertEqual(move_dest.date_deadline, new_deadline, msg='deadline date should be unchanged')

    def test_reordering_rule_1(self):
        # Required for `location_id` to be visible in the view
        self.product.is_storable = True
        self.env.user.group_ids += self.env.ref('stock.group_stock_multi_locations')
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = self.product
        orderpoint_form.product_min_qty = 0.0
        orderpoint_form.product_max_qty = 5.0
        orderpoint = orderpoint_form.save()

        # get auto-created pull rule from when warehouse is created
        rule = self.env['stock.rule'].search([
            ('route_id', '=', warehouse.reception_route_id.id),
            ('location_dest_id', '=', warehouse.lot_stock_id.id),
            ('location_src_id', '=', self.env.ref('stock.stock_location_suppliers').id),
            ('action', '=', 'pull'),
            ('procure_method', '=', 'make_to_stock'),
            ('picking_type_id', '=', warehouse.in_type_id.id)])

        # add a delay [i.e. lead days] so procurement will be triggered based on forecasted stock
        rule.delay = 9.0

        delivery_move = self.env['stock.move'].create({
            'date': datetime.today() + timedelta(days=5),
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12.0,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })
        delivery_move._action_confirm()
        orderpoint._compute_qty()
        self.env['stock.rule'].run_scheduler()

        receipt_move = self.env['stock.move'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', self.env.ref('stock.stock_location_suppliers').id)
        ])
        self.assertTrue(receipt_move)
        self.assertEqual(receipt_move.date.date(), date.today())
        self.assertEqual(receipt_move.product_uom_qty, 17.0)

    def test_reordering_rule_2(self):
        """Test when there is not enough product to assign a picking => automatically run
        reordering rule (RR). Add extra product to already confirmed picking => automatically
        run another RR
        """
        # Required for `location_id` to be visible in the view
        self.env.user.group_ids += self.env.ref('stock.group_stock_multi_locations')

        self.productA = self.env['product.product'].create({
            'name': 'Desk Combination',
            'is_storable': True,
        })

        self.productB = self.env['product.product'].create({
            'name': 'Desk Decoration',
            'is_storable': True,
        })

        warehouse = self.env['stock.warehouse'].search([], limit=1)
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = self.productA
        orderpoint_form.product_min_qty = 0.0
        orderpoint_form.product_max_qty = 5.0
        orderpoint = orderpoint_form.save()

        self.env['stock.warehouse.orderpoint'].create({
            'name': 'ProductB RR',
            'product_id': self.productB.id,
            'product_min_qty': 0,
            'product_max_qty': 5,
        })

        self.env['stock.rule'].create({
            'name': 'Rule Supplier',
            'route_id': warehouse.reception_route_id.id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'location_src_id': self.env.ref('stock.stock_location_suppliers').id,
            'action': 'pull',
            'delay': 9.0,
            'procure_method': 'make_to_stock',
            'picking_type_id': warehouse.in_type_id.id,
        })

        delivery_picking = self.env['stock.picking'].create({
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': self.ref('stock.picking_type_out'),
        })
        delivery_move = self.env['stock.move'].create({
            'product_id': self.productA.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12.0,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_id': delivery_picking.id,
        })
        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        receipt_move = self.env['stock.move'].search([
            ('product_id', '=', self.productA.id),
            ('location_id', '=', self.env.ref('stock.stock_location_suppliers').id)
        ])

        self.assertTrue(receipt_move)
        self.assertEqual(receipt_move.date.date(), date.today())
        self.assertEqual(receipt_move.product_uom_qty, 17.0)

        delivery_picking.write({'move_ids': [(0, 0, {
            'product_id': self.productB.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_id': delivery_picking.id,
            'additional': True
        })]})

        receipt_move2 = self.env['stock.move'].search([
            ('product_id', '=', self.productB.id),
            ('location_id', '=', self.env.ref('stock.stock_location_suppliers').id)
        ])

        self.assertTrue(receipt_move2)
        self.assertEqual(receipt_move2.date.date(), date.today())
        self.assertEqual(receipt_move2.product_uom_qty, 10.0)

    def test_reordering_rule_3(self):
        """Test how replenishment_uom_id affects qty_to_order"""
        stock_location = self.stock_location = self.env.ref('stock.stock_location_stock')
        self.productA = self.env['product.product'].create({
            'name': 'Desk Combination',
            'is_storable': True,
        })
        pack_of_10 = self.env['uom.uom'].create({
            'name': 'pack of 10',
            'relative_factor': 10.0,
            'relative_uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productA.id,
            'location_id': stock_location.id,
            'inventory_quantity': 14.5,
        }).action_apply_inventory()

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'name': 'ProductA RR',
            'product_id': self.productA.id,
            'product_min_qty': 15.0,
            'product_max_qty': 30.0,
            'replenishment_uom_id': pack_of_10.id,
        })
        self.assertEqual(orderpoint.qty_to_order, 20.0)  # 15.0 < 14.5 + 10 <= 30.0
        # Test search on computed field
        rr = self.env['stock.warehouse.orderpoint'].search([
            ('qty_to_order', '>', 0),
            ('product_id', '=', self.productA.id),
        ])
        self.assertTrue(rr)
        orderpoint.write({
            'replenishment_uom_id': self.env['uom.uom'].create({
                'name': 'Test UoM',
                'relative_factor': 1,
            })
        })
        self.assertEqual(orderpoint.qty_to_order, 16.0)  # 15.0 < 14.5 + 15 <= 30.0
        orderpoint.write({
            'replenishment_uom_id': False,
        })
        self.assertEqual(orderpoint.qty_to_order, 15.5)  # 15.0 < 14.5 + 15.5 <= 30.0

    def test_orderpoint_replenishment_view_1(self):
        """ Create two warehouses + two moves
        verify that the replenishment view is consistent"""
        warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse_2, warehouse_3 = self.env['stock.warehouse'].create([{
            'name': 'Warehouse Two',
            'code': 'WH2',
            'resupply_wh_ids': [warehouse_1.id],
        }, {
            'name': 'Warehouse Three',
            'code': 'WH3',
            'resupply_wh_ids': [warehouse_1.id],
        }])
        route_2 = self.env['stock.route'].search([
            ('supplied_wh_id', '=', warehouse_2.id),
            ('supplier_wh_id', '=', warehouse_1.id),
        ])
        route_3 = self.env['stock.route'].search([
            ('supplied_wh_id', '=', warehouse_3.id),
            ('supplier_wh_id', '=', warehouse_1.id),
        ])
        product = self.env['product.product'].create({
            'name': 'Super Product',
            'is_storable': True,
            'route_ids': [route_2.id, route_3.id]
        })
        moves = self.env['stock.move'].create([{
            'location_id': warehouse_2.lot_stock_id.id,
            'location_dest_id': self.partner.property_stock_customer.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1,
        }, {
            'location_id': warehouse_3.lot_stock_id.id,
            'location_dest_id': self.partner.property_stock_customer.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1,
        }])
        moves._action_confirm()
        # activate action of opening the replenishment view
        self.env.flush_all()
        self.env['stock.warehouse.orderpoint'].action_open_orderpoints()
        replenishments = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', product.id),
        ])
        # Verify that the location makes sense and that route is not set by default
        self.assertRecordValues(replenishments, [
            {'location_id': warehouse_2.lot_stock_id.id, 'route_id': False},
            {'location_id': warehouse_3.lot_stock_id.id, 'route_id': False},
        ])

    def test_orderpoint_replenishment_view_2(self):
        """ Create a warehouse  + location to replenish warehouse instead of main location
        verify that the orderpoints created are for the replenish locations not the warehouse main location"""
        warehouse_1 = self.env['stock.warehouse'].create({
            'name': 'Warehouse 1',
            'code': 'WH1',
        })
        warehouse_1.lot_stock_id.replenish_location = False
        replenish_loc = self.env['stock.location'].create({
            'name': 'Replenish Location',
            'location_id': warehouse_1.lot_stock_id.id,
            'replenish_location': True,
        })
        product = self.env['product.product'].create({
            'name': 'Rep Product',
            'is_storable': True,
        })
        move = self.env['stock.move'].create({
            'location_id': replenish_loc.id,
            'location_dest_id': self.partner.property_stock_customer.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 3,
        })
        move._action_confirm()
        # activate action of opening the replenishment view
        self.env.flush_all()
        self.env['stock.warehouse.orderpoint'].action_open_orderpoints()
        replenishments = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', product.id),
        ])
        # Verify the location and the qty
        self.assertRecordValues(replenishments, [
            {'location_id': replenish_loc.id, 'qty_to_order': 3},
        ])

    def test_orderpoint_replenishment_view_3(self):
        """
        Create a selectable on product route and a product without routes.
        Verify that none of the created orderpoints set the route by default.
        """
        stock_location = self.env.ref('stock.stock_location_stock')
        interdimensional_portal = self.env['stock.location'].create({
            'name': 'Interdimensional portal',
            'usage': 'internal',
            'location_id': stock_location.location_id.id,
        })
        lovely_route = self.env['stock.route'].create({
            'name': 'Lovely Route',
            'product_selectable': True,
            'product_categ_selectable': True,
            'sequence': 1,
            'rule_ids': [Command.create({
                'name': 'Interdimensional portal -> Stock',
                'action': 'pull',
                'picking_type_id': self.ref('stock.picking_type_internal'),
                'location_src_id': interdimensional_portal.id,
                'location_dest_id': stock_location.id,
            })],
        })
        lovely_category = self.env['product.category'].create({
            'name': 'Lovely Category',
            'route_ids': [Command.set(lovely_route.ids)]
        })
        products = self.env['product.product'].create([
            {
                'name': 'Lovely product',
                'is_storable': True,
                'route_ids': [Command.set([])],
            },
            {
                'name': 'Lovely product with route',
                'is_storable': True,
                'route_ids': [Command.set(lovely_route.ids)],
            },
            {
                'name': 'Lovely product with categ route',
                'is_storable': True,
                'route_ids': [Command.set([])],
                'categ_id': lovely_category.id,
            },
        ])
        moves = self.env['stock.move'].create([
            {
                'location_id': stock_location.id,
                'location_dest_id': self.partner.property_stock_customer.id,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': 1,
            } for product in products
        ])
        moves._action_confirm()
        # activate action of opening the replenishment view
        self.env.flush_all()
        self.env['stock.warehouse.orderpoint'].action_open_orderpoints()
        replenishments = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', 'in', products.ids),
        ])
        # Verify that the route is unset
        self.assertRecordValues(replenishments.sorted(lambda r: r.product_id.id), [
            {'product_id': products[0].id, 'location_id': stock_location.id, 'route_id': False},
            {'product_id': products[1].id, 'location_id': stock_location.id, 'route_id': False},
            {'product_id': products[2].id, 'location_id': stock_location.id, 'route_id': False},
        ])

    def test_orderpoint_compute_warehouse_location(self):
        warehouse_a = self.env['stock.warehouse'].search([], limit=1)
        warehouse_b = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH'
        })

        # No warehouse specified, no location specified
        # Must choose default/first warehouse and the `lot_stock_id` of that warehouse
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product.id,
        })
        self.assertEqual(orderpoint.warehouse_id, warehouse_a)
        self.assertEqual(orderpoint.location_id, warehouse_a.lot_stock_id)
        orderpoint.unlink()

        # Warehouse specified, must choose the `lot_stock_id` of that warehouse by default
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product.id,
            'warehouse_id': warehouse_b.id,
        })
        self.assertEqual(orderpoint.warehouse_id, warehouse_b)
        self.assertEqual(orderpoint.location_id, warehouse_b.lot_stock_id)
        orderpoint.unlink()

        # Location specified, must choose the warehouse of that location by default
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product.id,
            'location_id': warehouse_b.lot_stock_id.id,
        })
        self.assertEqual(orderpoint.warehouse_id, warehouse_b)
        self.assertEqual(orderpoint.location_id, warehouse_b.lot_stock_id)
        orderpoint.unlink()

        # Warehouse specified, location specified, must let them and not overwrite them with a default
        location = warehouse_b.lot_stock_id.copy()
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product.id,
            'warehouse_id': warehouse_b.id,
            'location_id': location.id,
        })
        self.assertEqual(orderpoint.warehouse_id, warehouse_b)
        self.assertEqual(orderpoint.location_id, location)
        orderpoint.unlink()

    def test_replenishment_order_to_max(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        self.product.is_storable = True
        self.env['stock.quant']._update_available_quantity(self.product, warehouse.lot_stock_id, 10)
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'name': 'ProductB RR',
            'product_id': self.product.id,
            'product_min_qty': 5,
            'product_max_qty': 200,
        })
        self.assertEqual(orderpoint.qty_forecast, 10.0)
        # above minimum qty => nothing to order
        orderpoint.action_replenish()
        self.assertEqual(orderpoint.qty_forecast, 10.0)
        orderpoint.action_replenish(force_to_max=True)
        self.assertEqual(orderpoint.qty_forecast, 200.0)

    def test_orderpoint_location_archive(self):
        warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH'
        })
        stock_loc = warehouse.lot_stock_id
        shelf1 = self.env['stock.location'].create({
            'location_id': stock_loc.id,
            'usage': 'internal',
            'name': 'shelf1'
        })
        product = self.env['product.product'].create({'name': 'Test Product', 'is_storable': True})
        stock_move = self.env['stock.move'].create({
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1,
            'location_id': shelf1.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        stock_move._action_confirm()
        shelf1.active = False
        # opening the replenishment should not raise a KeyError even if the location is archived
        self.env['stock.warehouse.orderpoint'].action_open_orderpoints()

    def test_compute_qty_to_order(self):
        """
        Check that the quantity to order is updated in the orderpoint when a new demand is created.
        """
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'name': 'auto orderpoint',
            'product_id': self.product.id,
            'product_min_qty': 5,
            'product_max_qty': 5,
            'qty_to_order': 5,
            'trigger': 'auto',
        })
        self.assertEqual(orderpoint.qty_to_order, 5)
        stock_move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })
        stock_move._action_confirm()
        self.assertEqual(orderpoint.qty_to_order, 6)

    def test_rule_help_message_mto_mtso(self):
        """Verify that the rule's help message correctly displays all relevant
        information when the procurement method is MTO or MTSO.
        """
        mto_rule = self.env.ref('stock.route_warehouse0_mto').rule_ids[0]
        source_mto = mto_rule.location_src_id.display_name
        self.assertIn(
            f'<br>A need is created in <b>{source_mto}</b> and a rule will be triggered to fulfill it.',
            mto_rule.rule_message,
            'The help message should correctly display information for MTO.'
        )
        # Switch to MTSO
        mto_rule.procure_method = 'mts_else_mto'
        source_mtso = mto_rule.location_src_id.display_name
        self.assertIn(
            f'<br>If the products are not available in <b>{source_mtso}</b>, a rule will be triggered to bring the missing quantity in this location.',
            mto_rule.rule_message,
            'The help message should correctly display information for MTSO.'
        )

    def test_replenishment_creation(self):
        """Test that the default replenishment order values
        are computed correctly in the tree view."""
        orderpoint_list_view = Form(self.env['stock.warehouse.orderpoint'], view='stock.view_warehouse_orderpoint_tree_editable')
        self.assertEqual(orderpoint_list_view.qty_to_order, 0)
        self.assertFalse(orderpoint_list_view.product_id)

    def test_orderpoint_warning(self):
        """ Checks that the warning correctly computes depending on the configuration. """
        self.product.is_storable = True
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product.id,
            'product_min_qty': 10,
            'product_max_qty': 50,
        })
        self.assertFalse(orderpoint.show_supply_warning, "There should at least be the rule from route 'My Company: Receive in 1 step (stock)'.")

        # Archive the route
        orderpoint.rule_ids.route_id.active = False
        orderpoint.invalidate_recordset(fnames=['show_supply_warning'])
        self.assertTrue(orderpoint.show_supply_warning)

        # Add a route to the product
        product_route = self.env['stock.route'].create({
            'name': 'Supplier -> Stock',
            'product_selectable': True,
            'rule_ids': [Command.create({
                'name': 'Supplier -> Stock',
                'action': 'pull',
                'picking_type_id': self.ref('stock.picking_type_in'),
                'location_src_id': self.ref('stock.stock_location_suppliers'),
                'location_dest_id': self.ref('stock.stock_location_stock'),
            })],
        })
        self.product.write({'route_ids': [Command.set(product_route.ids)]})
        orderpoint.invalidate_recordset(fnames=['show_supply_warning'])
        self.assertFalse(orderpoint.show_supply_warning)

    @freeze_time('2025-09-02 14:00:00')
    def test_orderpoint_deadline_date(self):
        """ Test that the deadline date is correctly computed. """
        self.product.is_storable = True
        product_1 = self.env['product.product'].create({
            'name': 'product_1',
            'type': 'consu',
            'is_storable': True,
        })
        product_2 = self.env['product.product'].create({
            'name': 'product_2',
            'type': 'consu',
            'is_storable': True,
        })

        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 20,
        })
        self.env['stock.quant'].create({
            'product_id': product_1.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 20,
        })
        self.env['stock.quant'].create({
            'product_id': product_2.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 20,
        })
        orderpoint_0 = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product.id,
            'product_min_qty': 10,
            'product_max_qty': 50,
        })
        orderpoint_1 = self.env['stock.warehouse.orderpoint'].create({
            'product_id': product_1.id,
            'product_min_qty': 10,
            'product_max_qty': 50,
        })
        orderpoint_2 = self.env['stock.warehouse.orderpoint'].create({
            'product_id': product_2.id,
            'product_min_qty': 10,
            'product_max_qty': 50,
        })

        delivery_date_0 = datetime.today() + timedelta(days=15)
        delivery_date_1 = datetime.today() + timedelta(days=25)
        delivery_date_2 = datetime.today() + timedelta(days=35)

        stock_moves = self.env['stock.move']
        # product 0: 15 OUT in 15 days, 10 IN in 25 days -> deadline in 15 days
        stock_moves |= self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 15,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'date': delivery_date_0,
        })
        stock_moves |= self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 10,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock'),
            'date': delivery_date_1,
        })
        # product 1: 10 OUT in 25, 5 OUT in 35 days -> deadline in 35 days
        stock_moves |= self.env['stock.move'].create({
            'product_id': product_1.id,
            'product_uom': product_1.uom_id.id,
            'product_uom_qty': 10,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'date': delivery_date_1,
        })
        stock_moves |= self.env['stock.move'].create({
            'product_id': product_1.id,
            'product_uom': product_1.uom_id.id,
            'product_uom_qty': 5,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'date': delivery_date_2,
        })
        # product 2: 15 OUT in 15 days, 15 IN in 15 days, 15 OUT in 25 days -> deadline in 25 days
        stock_moves |= self.env['stock.move'].create({
            'product_id': product_2.id,
            'product_uom': product_2.uom_id.id,
            'product_uom_qty': 15,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'date': delivery_date_0,
        })
        stock_moves |= self.env['stock.move'].create({
            'product_id': product_2.id,
            'product_uom': product_2.uom_id.id,
            'product_uom_qty': 15,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock'),
            'date': delivery_date_0,
        })
        stock_moves |= self.env['stock.move'].create({
            'product_id': product_2.id,
            'product_uom': product_2.uom_id.id,
            'product_uom_qty': 15,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'date': delivery_date_1,
        })

        # There should be no deadline since no move was confirmed
        self.assertEqual(orderpoint_0.deadline_date, False)
        self.assertEqual(orderpoint_1.deadline_date, False)
        self.assertEqual(orderpoint_2.deadline_date, False)
        # After confirming the moves, deadline dates should have been applied to all orderpoints
        stock_moves._action_confirm()
        self.assertEqual(orderpoint_0.deadline_date, delivery_date_0.date())
        self.assertEqual(orderpoint_1.deadline_date, delivery_date_2.date())
        self.assertEqual(orderpoint_2.deadline_date, delivery_date_1.date())
        # After changing the horizon days, the deadline dates should have been recomputed
        self.env.company.horizon_days = 30
        self.assertEqual(orderpoint_0.deadline_date, delivery_date_0.date())
        self.assertEqual(orderpoint_1.deadline_date, False)
        self.assertEqual(orderpoint_2.deadline_date, delivery_date_1.date())

    @freeze_time('2025-08-14 10:00:00')
    def test_orderpoint_wizard_graph(self):
        """ Test that the graph data is correctly computed. """
        self.product.is_storable = True
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product.id,
            'product_min_qty': 10,
            'product_max_qty': 50,
        })

        warehouse = self.env['stock.warehouse'].search([], limit=1)
        out_move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })
        out_move._action_confirm()
        out_move._action_assign()
        out_move.quantity = 15
        out_move.picked = True
        out_move._action_done()

        info = self.env['stock.replenishment.info'].create({'orderpoint_id': orderpoint.id})
        graph_data = loads(info.json_replenishment_graph)
        self.assertEqual(graph_data['daily_demand'], 0.48)
        self.assertEqual(graph_data['average_stock'], 30.0)
        self.assertEqual(graph_data['ordering_period'], 82.0)
        self.assertListEqual(graph_data['x_axis_vals'], ['', 'In 82 day(s)', 'In 164 day(s)', 'In 246 day(s)'])
        self.assertListEqual([curve_line_val['y'] for curve_line_val in graph_data['curve_line_vals']], [50, 10, 50, 10, 50, 10])

        info.write({
            'based_on': 'one_week',
            'percent_factor': 200,
            'product_min_qty': 20,
            'product_max_qty': 40,
        })
        graph_data = loads(info.json_replenishment_graph)
        self.assertEqual(graph_data['daily_demand'], 4.29)
        self.assertEqual(graph_data['average_stock'], 30.0)
        self.assertEqual(graph_data['ordering_period'], 4.0)
        self.assertListEqual(graph_data['x_axis_vals'], ['', 'In 4 day(s)', 'In 8 day(s)', 'In 12 day(s)'])
        self.assertListEqual([curve_line_val['y'] for curve_line_val in graph_data['curve_line_vals']], [40, 20, 40, 20, 40, 20])

        late_out_move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'date': datetime.today() - timedelta(days=5),
        })
        late_out_move._action_confirm()
        info._compute_json_replenishment_graph()
        graph_data = loads(info.json_replenishment_graph)
        self.assertEqual(graph_data['daily_demand'], 8.57)
        self.assertEqual(graph_data['average_stock'], 30.0)
        self.assertEqual(graph_data['ordering_period'], 2.0)
        self.assertListEqual(graph_data['x_axis_vals'], ['', 'In 2 day(s)', 'In 4 day(s)', 'In 6 day(s)'])
        self.assertListEqual([curve_line_val['y'] for curve_line_val in graph_data['curve_line_vals']], [40, 20, 40, 20, 40, 20])


class TestProcRuleLoad(TransactionCase):
    def setUp(cls):
        super(TestProcRuleLoad, cls).setUp()
        cls.skipTest("Performance test, too heavy to run.")

    def test_orderpoint_1(self):
        """ Try 500 products with a 1000 RR(stock -> shelf1 and stock -> shelf2)
        Also randomly include 4 miss configuration.
        """
        warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH'
        })
        warehouse.reception_steps = 'three_steps'
        supplier_loc = self.env.ref('stock.stock_location_suppliers')
        stock_loc = warehouse.lot_stock_id
        shelf1 = self.env['stock.location'].create({
            'location_id': stock_loc.id,
            'usage': 'internal',
            'name': 'shelf1'
        })
        shelf2 = self.env['stock.location'].create({
            'location_id': stock_loc.id,
            'usage': 'internal',
            'name': 'shelf2'
        })

        products = self.env['product.product'].create([{'name': i, 'is_storable': True} for i in range(500)])
        self.env['stock.warehouse.orderpoint'].create([{
            'product_id': products[i // 2].id,
            'location_id': (i % 2 == 0) and shelf1.id or shelf2.id,
            'warehouse_id': warehouse.id,
            'product_min_qty': 5,
            'product_max_qty': 10,
        } for i in range(1000)])

        self.env['stock.rule'].create({
            'name': 'Rule Shelf1',
            'route_id': warehouse.reception_route_id.id,
            'location_dest_id': shelf1.id,
            'location_src_id': stock_loc.id,
            'action': 'pull',
            'procure_method': 'make_to_order',
            'picking_type_id': warehouse.int_type_id.id,
        })
        self.env['stock.rule'].create({
            'name': 'Rule Shelf2',
            'route_id': warehouse.reception_route_id.id,
            'location_dest_id': shelf2.id,
            'location_src_id': stock_loc.id,
            'action': 'pull',
            'procure_method': 'make_to_order',
            'picking_type_id': warehouse.int_type_id.id,
        })
        self.env['stock.rule'].create({
            'name': 'Rule Supplier',
            'route_id': warehouse.reception_route_id.id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
            'location_src_id': supplier_loc.id,
            'action': 'pull',
            'procure_method': 'make_to_stock',
            'picking_type_id': warehouse.in_type_id.id,
        })

        wrong_route = self.env['stock.route'].create({
            'name': 'Wrong Route',
        })
        self.env['stock.rule'].create({
            'name': 'Trap Rule',
            'route_id': wrong_route.id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
            'location_src_id': supplier_loc.id,
            'action': 'pull',
            'procure_method': 'make_to_order',
            'picking_type_id': warehouse.in_type_id.id,
        })
        (products[50] | products[99] | products[150] | products[199]).write({
            'route_ids': [(4, wrong_route.id)]
        })
        self.env['stock.rule'].run_scheduler()
        self.assertTrue(self.env['stock.move'].search([('product_id', 'in', products.ids)]))
        for index in [50, 99, 150, 199]:
            self.assertTrue(self.env['mail.activity'].search([
                ('res_id', '=', products[index].product_tmpl_id.id),
                ('res_model_id', '=', self.env.ref('product.model_product_template').id)
            ]))
