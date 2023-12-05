# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo.tests.common import Form, TransactionCase
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
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = self.product
        orderpoint_form.location_id = self.env.ref('stock.stock_location_stock')
        orderpoint_form.product_min_qty = 4.0
        orderpoint_form.product_max_qty = 5.1
        orderpoint_form.qty_multiple = 0.1
        orderpoint = orderpoint_form.save()
        self.assertEqual(orderpoint.qty_to_order, orderpoint.product_max_qty)

    def test_endless_loop_rules_from_location(self):
        """ Creates and configure a rule the way, when trying to get rules from
        location, it goes in a state where the found rule tries to trigger another
        rule but finds nothing else than itself and so get stuck in a recursion error."""
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        reception_route = warehouse.reception_route_id
        self.product.type = 'product'

        # Creates a delivery for this product, that way, this product will be to resupply.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = warehouse.out_type_id
        with picking_form.move_ids_without_package.new() as move_line:
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
                'name': '/',
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
        pick_output.move_ids._onchange_product_id()

        # Confirm delivery order.
        pick_output.action_confirm()

        # I run the scheduler.
        # Note: If purchase if already installed, the method _run_buy will be called due
        # to the purchase demo data. As we update the stock module to run this test, the
        # method won't be an attribute of stock.procurement at this moment. For that reason
        # we mute the logger when running the scheduler.
        with mute_logger('odoo.addons.stock.models.procurement'):
            self.env['procurement.group'].run_scheduler()

        # Check that a picking was created from stock to output.
        moves = self.env['stock.move'].search([
            ('product_id', '=', self.product.id),
            ('location_id', '=', self.ref('stock.stock_location_stock')),
            ('location_dest_id', '=', self.ref('stock.stock_location_output')),
            ('move_dest_ids', 'in', [pick_output.move_ids[0].id])
        ])
        self.assertEqual(len(moves.ids), 1, "It should have created a picking from Stock to Output with the original picking as destination")

    def test_propagate_deadline_move(self):
        deadline = datetime.now()
        move_dest = self.env['stock.move'].create({
            'name': 'move_dest',
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'date_deadline': deadline,
            'location_id': self.ref('stock.stock_location_output'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })

        move_orig = self.env['stock.move'].create({
            'name': 'move_orig',
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
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')
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
            'name': 'Delivery',
            'date': datetime.today() + timedelta(days=5),
            'product_id': self.product.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12.0,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
        })
        delivery_move._action_confirm()
        orderpoint._compute_qty()
        self.env['procurement.group'].run_scheduler()

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
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')

        self.productA = self.env['product.product'].create({
            'name': 'Desk Combination',
            'type': 'product',
        })

        self.productB = self.env['product.product'].create({
            'name': 'Desk Decoration',
            'type': 'product',
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
            'name': 'Delivery',
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
            'name': 'Extra Move',
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

    def test_fixed_procurement_01(self):
        """ Run a procurement for 5 products when there are only 4 in stock then
        check that MTO is applied on the moves when the rule is set to 'mts_else_mto'
        """
        self.partner = self.env['res.partner'].create({'name': 'Partner'})
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse.delivery_steps = 'pick_ship'
        final_location = self.partner.property_stock_customer

        # Create a product and add 10 units in stock
        product_a = self.env['product.product'].create({
            'name': 'ProductA',
            'type': 'product',
        })
        self.env['stock.quant']._update_available_quantity(product_a, warehouse.lot_stock_id, 10.0)

        # Create a route which will allows 'wave picking'
        wave_pg = self.env['procurement.group'].create({'name': 'Wave PG'})
        wave_route = self.env['stock.route'].create({
            'name': 'Wave for ProductA',
            'product_selectable': True,
            'sequence': 1,
            'rule_ids': [(0, 0, {
                'name': 'Stock -> output rule',
                'action': 'pull',
                'picking_type_id': self.ref('stock.picking_type_internal'),
                'location_src_id': self.ref('stock.stock_location_stock'),
                'location_dest_id': self.ref('stock.stock_location_output'),
                'group_propagation_option': 'fixed',
                'group_id': wave_pg.id,
            })],
        })

        # Set this route on `product_a`
        product_a.write({
            'route_ids': [(4, wave_route.id)]
        })

        # Create a procurement for 2 units
        pg = self.env['procurement.group'].create({'name': 'Wave 1'})
        self.env['procurement.group'].run([
            pg.Procurement(
                product_a,
                2.0,
                product_a.uom_id,
                final_location,
                'wave_part_1',
                'wave_part_1',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'group_id': pg
                }
            )
        ])

        # 2 pickings should be created: 1 for pick, 1 for ship
        picking_pick = self.env['stock.picking'].search([('group_id', '=', wave_pg.id)])
        picking_ship = self.env['stock.picking'].search([('group_id', '=', pg.id)])
        self.assertAlmostEqual(picking_pick.move_ids.product_uom_qty, 2.0)
        self.assertAlmostEqual(picking_ship.move_ids.product_uom_qty, 2.0)

        # Create a procurement for 3 units
        pg = self.env['procurement.group'].create({'name': 'Wave 2'})
        self.env['procurement.group'].run([
            pg.Procurement(
                product_a,
                3.0,
                product_a.uom_id,
                final_location,
                'wave_part_2',
                'wave_part_2',
                warehouse.company_id,
                {
                    'warehouse_id': warehouse,
                    'group_id': pg
                }
            )
        ])

        # The picking for the pick operation should be reused and the lines merged.
        picking_ship = self.env['stock.picking'].search([('group_id', '=', pg.id)])
        self.assertAlmostEqual(picking_pick.move_ids.product_uom_qty, 5.0)
        self.assertAlmostEqual(picking_ship.move_ids.product_uom_qty, 3.0)

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
            'type': 'product',
            'route_ids': [route_2.id, route_3.id]
        })
        moves = self.env['stock.move'].create([{
            'name': 'Move WH2',
            'location_id': warehouse_2.lot_stock_id.id,
            'location_dest_id': self.partner.property_stock_customer.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1,
        }, {
            'name': 'Move WH3',
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
        # Verify that the location and the route make sense
        self.assertRecordValues(replenishments, [
            {'location_id': warehouse_2.lot_stock_id.id, 'route_id': route_2.id},
            {'location_id': warehouse_3.lot_stock_id.id, 'route_id': route_3.id},
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
            'type': 'product',
        })
        move = self.env['stock.move'].create({
            'name': 'Move WH2',
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
        self.product.detailed_type = 'product'
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

        products = self.env['product.product'].create([{'name': i, 'type': 'product'} for i in range(500)])
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
        self.env['procurement.group'].run_scheduler()
        self.assertTrue(self.env['stock.move'].search([('product_id', 'in', products.ids)]))
        for index in [50, 99, 150, 199]:
            self.assertTrue(self.env['mail.activity'].search([
                ('res_id', '=', products[index].product_tmpl_id.id),
                ('res_model_id', '=', self.env.ref('product.model_product_template').id)
            ]))
