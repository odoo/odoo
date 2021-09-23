# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.exceptions import UserError


class TestProcurement(TestMrpCommon):

    def test_procurement(self):
        """This test case when create production order check procurement is create"""
        # Update BOM
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_5).unlink()
        self.bom_1.bom_line_ids.filtered(lambda x: x.product_id == self.product_1).unlink()
        # Update route
        self.warehouse = self.env.ref('stock.warehouse0')
        self.warehouse.mto_pull_id.route_id.active = True
        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id
        self.product_4.write({'route_ids': [(6, 0, [route_manufacture, route_mto])]})

        # Create production order
        # -------------------------
        # Product6 Unit 24
        #    Product4 8 Dozen
        #    Product2 12 Unit
        # -----------------------

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product_6
        production_form.bom_id = self.bom_3
        production_form.product_qty = 24
        production_form.product_uom_id = self.product_6.uom_id
        production_product_6 = production_form.save()
        production_product_6.action_confirm()
        production_product_6.action_assign()

        # check production state is Confirmed
        self.assertEqual(production_product_6.state, 'confirmed')

        # Check procurement for product 4 created or not.
        # Check it created a purchase order

        move_raw_product4 = production_product_6.move_raw_ids.filtered(lambda x: x.product_id == self.product_4)
        produce_product_4 = self.env['mrp.production'].search([('product_id', '=', self.product_4.id),
                                                               ('move_dest_ids', '=', move_raw_product4[0].id)])
        # produce product
        self.assertEqual(produce_product_4.reservation_state, 'confirmed', "Consume material not available")

        # Create production order
        # -------------------------
        # Product 4  96 Unit
        #    Product2 48 Unit
        # ---------------------
        # Update Inventory
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_2.id,
            'inventory_quantity': 48,
            'location_id': self.warehouse.lot_stock_id.id,
        }).action_apply_inventory()
        produce_product_4.action_assign()
        self.assertEqual(produce_product_4.product_qty, 8, "Wrong quantity of finish product.")
        self.assertEqual(produce_product_4.product_uom_id, self.uom_dozen, "Wrong quantity of finish product.")
        self.assertEqual(produce_product_4.reservation_state, 'assigned', "Consume material not available")

        # produce product4
        # ---------------

        mo_form = Form(produce_product_4)
        mo_form.qty_producing = produce_product_4.product_qty
        produce_product_4 = mo_form.save()
        # Check procurement and Production state for product 4.
        produce_product_4.button_mark_done()
        self.assertEqual(produce_product_4.state, 'done', 'Production order should be in state done')

        # Produce product 6
        # ------------------

        # Update Inventory
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_2.id,
            'inventory_quantity': 12,
            'location_id': self.warehouse.lot_stock_id.id,
        }).action_apply_inventory()
        production_product_6.action_assign()

        # ------------------------------------

        self.assertEqual(production_product_6.reservation_state, 'assigned', "Consume material not available")
        mo_form = Form(production_product_6)
        mo_form.qty_producing = production_product_6.product_qty
        production_product_6 = mo_form.save()
        # Check procurement and Production state for product 6.
        production_product_6.button_mark_done()
        self.assertEqual(production_product_6.state, 'done', 'Production order should be in state done')
        self.assertEqual(self.product_6.qty_available, 24, 'Wrong quantity available of finished product.')

    def test_procurement_2(self):
        """Check that a manufacturing order create the right procurements when the route are set on
        a parent category of a product"""
        # find a child category id
        all_categ_id = self.env['product.category'].search([('parent_id', '=', None)], limit=1)
        child_categ_id = self.env['product.category'].search([('parent_id', '=', all_categ_id.id)], limit=1)

        # set the product of `self.bom_1` to this child category
        for bom_line_id in self.bom_1.bom_line_ids:
            # check that no routes are defined on the product
            self.assertEqual(len(bom_line_id.product_id.route_ids), 0)
            # set the category of the product to a child category
            bom_line_id.product_id.categ_id = child_categ_id

        # set the MTO route to the parent category (all)
        self.warehouse = self.env.ref('stock.warehouse0')
        mto_route = self.warehouse.mto_pull_id.route_id
        mto_route.active = True
        mto_route.product_categ_selectable = True
        all_categ_id.write({'route_ids': [(6, 0, [mto_route.id])]})

        # create MO, but check it raises error as components are in make to order and not everyone has
        with self.assertRaises(UserError):
            production_form = Form(self.env['mrp.production'])
            production_form.product_id = self.product_4
            production_form.product_uom_id = self.product_4.uom_id
            production_form.product_qty = 1
            production_product_4 = production_form.save()
            production_product_4.action_confirm()

    def test_procurement_3(self):
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        warehouse.write({'reception_steps': 'three_steps'})
        warehouse.mto_pull_id.route_id.active = True
        self.env['stock.location']._parent_store_compute()
        warehouse.reception_route_id.rule_ids.filtered(
            lambda p: p.location_src_id == warehouse.wh_input_stock_loc_id and
            p.location_id == warehouse.wh_qc_stock_loc_id).write({
                'procure_method': 'make_to_stock'
            })

        finished_product = self.env['product.product'].create({
            'name': 'Finished Product',
            'type': 'product',
        })
        component = self.env['product.product'].create({
            'name': 'Component',
            'type': 'product',
            'route_ids': [(4, warehouse.mto_pull_id.route_id.id)]
        })
        self.env['stock.quant']._update_available_quantity(component, warehouse.wh_input_stock_loc_id, 100)
        bom = self.env['mrp.bom'].create({
            'product_id': finished_product.id,
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1.0})
            ]})
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.bom_id = bom
        mo_form.product_qty = 5
        mo_form.product_uom_id = finished_product.uom_id
        mo_form.location_src_id = warehouse.lot_stock_id
        mo = mo_form.save()
        mo.action_confirm()
        pickings = self.env['stock.picking'].search([('product_id', '=', component.id)])
        self.assertEqual(len(pickings), 2.0)
        picking_input_to_qc = pickings.filtered(lambda p: p.location_id == warehouse.wh_input_stock_loc_id)
        picking_qc_to_stock = pickings - picking_input_to_qc
        self.assertTrue(picking_input_to_qc)
        self.assertTrue(picking_qc_to_stock)
        picking_input_to_qc.action_assign()
        self.assertEqual(picking_input_to_qc.state, 'assigned')
        picking_input_to_qc.move_line_ids.write({'qty_done': 5.0})
        picking_input_to_qc._action_done()
        picking_qc_to_stock.action_assign()
        self.assertEqual(picking_qc_to_stock.state, 'assigned')
        picking_qc_to_stock.move_line_ids.write({'qty_done': 3.0})
        picking_qc_to_stock.with_context(skip_backorder=True, picking_ids_not_to_backorder=picking_qc_to_stock.ids).button_validate()
        self.assertEqual(picking_qc_to_stock.state, 'done')
        mo.action_assign()
        self.assertEqual(mo.move_raw_ids.reserved_availability, 3.0)
        produce_form = Form(mo)
        produce_form.qty_producing = 3.0
        mo = produce_form.save()
        self.assertEqual(mo.move_raw_ids.quantity_done, 3.0)
        picking_qc_to_stock.move_line_ids.qty_done = 5.0
        self.assertEqual(mo.move_raw_ids.reserved_availability, 5.0)
        self.assertEqual(mo.move_raw_ids.quantity_done, 3.0)

    def test_link_date_mo_moves(self):
        """ Check link of shedule date for manufaturing with date stock move."""

        # create a product with manufacture route
        product_1 = self.env['product.product'].create({
            'name': 'AAA',
            'route_ids': [(4, self.ref('mrp.route_warehouse0_manufacture'))]
        })

        component_1 = self.env['product.product'].create({
            'name': 'component',
        })

        self.env['mrp.bom'].create({
            'product_id': product_1.id,
            'product_tmpl_id': product_1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component_1.id, 'product_qty': 1}),
            ]})

        # create a move for product_1 from stock to output and reserve to trigger the
        # rule
        move_dest = self.env['stock.move'].create({
            'name': 'move_orig',
            'product_id': product_1.id,
            'product_uom': self.ref('uom.product_uom_unit'),
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            'product_uom_qty': 10,
            'procure_method': 'make_to_order'
        })

        move_dest._action_confirm()
        mo = self.env['mrp.production'].search([
            ('product_id', '=', product_1.id),
            ('state', '=', 'confirmed')
        ])

        self.assertAlmostEqual(mo.move_finished_ids.date, mo.move_raw_ids.date + timedelta(hours=1), delta=timedelta(seconds=1))

        self.assertEqual(len(mo), 1, 'the manufacture order is not created')

        mo_form = Form(mo)
        self.assertEqual(mo_form.product_qty, 10, 'the quantity to produce is not good relative to the move')

        mo = mo_form.save()

        # Confirming mo create finished move
        move_orig = self.env['stock.move'].search([
            ('move_dest_ids', 'in', move_dest.ids)
        ], limit=1)

        self.assertEqual(len(move_orig), 1, 'the move orig is not created')
        self.assertEqual(move_orig.product_qty, 10, 'the quantity to produce is not good relative to the move')

        new_sheduled_date = fields.Datetime.to_datetime(mo.date_planned_start) + timedelta(days=5)
        mo_form = Form(mo)
        mo_form.date_planned_start = new_sheduled_date
        mo = mo_form.save()

        self.assertAlmostEqual(mo.move_raw_ids.date, mo.date_planned_start, delta=timedelta(seconds=1))
        self.assertAlmostEqual(mo.move_finished_ids.date, mo.date_planned_finished, delta=timedelta(seconds=1))

    def test_finished_move_cancellation(self):
        """Check state of finished move on cancellation of raw moves. """
        product_bottle = self.env['product.product'].create({
            'name': 'Plastic Bottle',
            'route_ids': [(4, self.ref('mrp.route_warehouse0_manufacture'))]
        })

        component_mold = self.env['product.product'].create({
            'name': 'Plastic Mold',
        })

        self.env['mrp.bom'].create({
            'product_id': product_bottle.id,
            'product_tmpl_id': product_bottle.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component_mold.id, 'product_qty': 1}),
            ]})

        move_dest = self.env['stock.move'].create({
            'name': 'move_bottle',
            'product_id': product_bottle.id,
            'product_uom': self.ref('uom.product_uom_unit'),
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            'product_uom_qty': 10,
            'procure_method': 'make_to_order',
        })

        move_dest._action_confirm()
        mo = self.env['mrp.production'].search([
            ('product_id', '=', product_bottle.id),
            ('state', '=', 'confirmed')
        ])
        mo.move_raw_ids[0]._action_cancel()
        self.assertEqual(mo.state, 'cancel', 'Manufacturing order should be cancelled.')
        self.assertEqual(mo.move_finished_ids[0].state, 'cancel', 'Finished move should be cancelled if mo is cancelled.')
        self.assertEqual(mo.move_dest_ids[0].state, 'waiting', 'Destination move should not be cancelled if prapogation cancel is False on manufacturing rule.')

    def test_procurement_with_empty_bom(self):
        """Ensure that a procurement request using a product with an empty BoM
        will create an empty MO in confirmed state that can be completed afterwards.
        """
        self.warehouse = self.env.ref('stock.warehouse0')
        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id
        product = self.env['product.product'].create({
            'name': 'Clafoutis',
            'route_ids': [(6, 0, [route_manufacture, route_mto])]
        })
        self.env['mrp.bom'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
        })
        move_dest = self.env['stock.move'].create({
            'name': 'Customer MTO Move',
            'product_id': product.id,
            'product_uom': self.ref('uom.product_uom_unit'),
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            'product_uom_qty': 10,
            'procure_method': 'make_to_order',
        })
        move_dest._action_confirm()

        production = self.env['mrp.production'].search([('product_id', '=', product.id)])
        self.assertTrue(production)
        self.assertFalse(production.move_raw_ids)
        self.assertEqual(production.state, 'confirmed')

        comp1 = self.env['product.product'].create({
            'name': 'egg',
        })
        move_values = production._get_move_raw_values(comp1, 40.0, self.env.ref('uom.product_uom_unit'))
        self.env['stock.move'].create(move_values)

        production.action_confirm()
        produce_form = Form(production)
        produce_form.qty_producing = production.product_qty
        production = produce_form.save()
        production.button_mark_done()

        move_dest._action_assign()
        self.assertEqual(move_dest.reserved_availability, 10.0)

    def test_auto_assign(self):
        """ When auto reordering rule exists, check for when:
        1. There is not enough of a manufactured product to assign (reserve for) a picking => auto-create 1st MO
        2. There is not enough of a manufactured component to assign the created MO => auto-create 2nd MO
        3. Add an extra manufactured component (not in stock) to 1st MO => auto-create 3rd MO
        4. When 2nd MO is completed => auto-assign to 1st MO
        5. When 1st MO is completed => auto-assign to picking
        6. Additionally check that a MO that has component in stock auto-reserves when MO is confirmed (since default setting = 'at_confirm')"""

        self.warehouse = self.env.ref('stock.warehouse0')
        route_manufacture = self.warehouse.manufacture_pull_id.route_id

        product_1 = self.env['product.product'].create({
            'name': 'Cake',
            'type': 'product',
            'route_ids': [(6, 0, [route_manufacture.id])]
        })
        product_2 = self.env['product.product'].create({
            'name': 'Cake Mix',
            'type': 'product',
            'route_ids': [(6, 0, [route_manufacture.id])]
        })
        product_3 = self.env['product.product'].create({
            'name': 'Flour',
            'type': 'consu',
        })

        bom1 = self.env['mrp.bom'].create({
            'product_id': product_1.id,
            'product_tmpl_id': product_1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1,
            'consumption': 'flexible',
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_2.id, 'product_qty': 1}),
            ]})

        self.env['mrp.bom'].create({
            'product_id': product_2.id,
            'product_tmpl_id': product_2.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_3.id, 'product_qty': 1}),
            ]})

        # extra manufactured component added to 1st MO after it is already confirmed
        product_4 = self.env['product.product'].create({
            'name': 'Flavor Enchancer',
            'type': 'product',
            'route_ids': [(6, 0, [route_manufacture.id])]
        })
        product_5 = self.env['product.product'].create({
            'name': 'MSG',
            'type': 'consu',
        })

        self.env['mrp.bom'].create({
            'product_id': product_4.id,
            'product_tmpl_id': product_4.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_5.id, 'product_qty': 1}),
            ]})

        # setup auto orderpoints (reordering rules)
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'Cake RR',
            'location_id': self.warehouse.lot_stock_id.id,
            'product_id': product_1.id,
            'product_min_qty': 0,
            'product_max_qty': 5,
        })

        self.env['stock.warehouse.orderpoint'].create({
            'name': 'Cake Mix RR',
            'location_id': self.warehouse.lot_stock_id.id,
            'product_id': product_2.id,
            'product_min_qty': 0,
            'product_max_qty': 5,
        })

        self.env['stock.warehouse.orderpoint'].create({
            'name': 'Flavor Enchancer RR',
            'location_id': self.warehouse.lot_stock_id.id,
            'product_id': product_4.id,
            'product_min_qty': 0,
            'product_max_qty': 5,
        })

        # create picking output to trigger creating MO for reordering product_1
        pick_output = self.env['stock.picking'].create({
            'name': 'Cake Delivery Order',
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_lines': [(0, 0, {
                'name': '/',
                'product_id': product_1.id,
                'product_uom': product_1.uom_id.id,
                'product_uom_qty': 10.00,
                'procure_method': 'make_to_stock',
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        })
        pick_output.action_confirm()  # should trigger orderpoint to create and confirm 1st MO
        pick_output.action_assign()

        mo = self.env['mrp.production'].search([
            ('product_id', '=', product_1.id),
            ('state', '=', 'confirmed')
        ])

        self.assertEqual(len(mo), 1, "Manufacture order was not automatically created")
        mo.action_assign()
        mo.is_locked = False
        self.assertEqual(mo.move_raw_ids.reserved_availability, 0, "No components should be reserved yet")
        self.assertEqual(mo.product_qty, 15, "Quantity to produce should be picking demand + reordering rule max qty")

        # 2nd MO for product_2 should have been created and confirmed when 1st MO for product_1 was confirmed
        mo2 = self.env['mrp.production'].search([
            ('product_id', '=', product_2.id),
            ('state', '=', 'confirmed')
        ])

        self.assertEqual(len(mo2), 1, 'Second manufacture order was not created')
        self.assertEqual(mo2.product_qty, 20, "Quantity to produce should be MO's 'to consume' qty + reordering rule max qty")
        mo2_form = Form(mo2)
        mo2_form.qty_producing = 20
        mo2 = mo2_form.save()
        mo2.button_mark_done()

        self.assertEqual(mo.move_raw_ids.reserved_availability, 15, "Components should have been auto-reserved")

        # add new component to 1st MO
        mo_form = Form(mo)
        with mo_form.move_raw_ids.new() as line:
            line.product_id = product_4
            line.product_uom_qty = 1
        mo_form.save()  # should trigger orderpoint to create and confirm 3rd MO

        mo3 = self.env['mrp.production'].search([
            ('product_id', '=', product_4.id),
            ('state', '=', 'confirmed')
        ])

        self.assertEqual(len(mo3), 1, 'Third manufacture order for added component was not created')
        self.assertEqual(mo3.product_qty, 6, "Quantity to produce should be 1 + reordering rule max qty")

        mo_form = Form(mo)
        mo.move_raw_ids.quantity_done = 15
        mo_form.qty_producing = 15
        mo = mo_form.save()
        mo.button_mark_done()

        self.assertEqual(pick_output.move_ids_without_package.reserved_availability, 10, "Completed products should have been auto-reserved in picking")

        # make sure next MO auto-reserves components now that they are in stock since
        # default reservation_method = 'at_confirm'
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_1
        mo_form.bom_id = bom1
        mo_form.product_qty = 5
        mo_form.product_uom_id = product_1.uom_id
        mo_assign_at_confirm = mo_form.save()
        mo_assign_at_confirm.action_confirm()

        self.assertEqual(mo_assign_at_confirm.move_raw_ids.reserved_availability, 5, "Components should have been auto-reserved")

    def test_check_update_qty_mto_chain(self):
        """ Simulate a mto chain with a manufacturing order. Updating the
        initial demand should also impact the initial move but not the
        linked manufacturing order.
        """
        def create_run_procurement(product, product_qty, values=None):
            if not values:
                values = {
                    'warehouse_id': picking_type_out.warehouse_id,
                    'action': 'pull_push',
                    'group_id': procurement_group,
                }
            return self.env['procurement.group'].run([self.env['procurement.group'].Procurement(
                product, product_qty, self.uom_unit, vendor.property_stock_customer,
                product.name, '/', self.env.company, values)
            ])

        picking_type_out = self.env.ref('stock.picking_type_out')
        vendor = self.env['res.partner'].create({
            'name': 'Roger'
        })
        # This needs to be tried with MTO route activated
        self.env['stock.location.route'].browse(self.ref('stock.route_warehouse0_mto')).action_unarchive()
        # Define products requested for this BoM.
        product = self.env['product.product'].create({
            'name': 'product',
            'type': 'product',
            'route_ids': [(4, self.ref('stock.route_warehouse0_mto')), (4, self.ref('mrp.route_warehouse0_manufacture'))],
            'categ_id': self.env.ref('product.product_category_all').id
        })
        component = self.env['product.product'].create({
            'name': 'component',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id
        })
        self.env['mrp.bom'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': product.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1}),
            ]
        })

        procurement_group = self.env['procurement.group'].create({
            'move_type': 'direct',
            'partner_id': vendor.id
        })
        # Create initial procurement that will generate the initial move and its picking.
        create_run_procurement(product, 10, {
            'group_id': procurement_group,
            'warehouse_id': picking_type_out.warehouse_id,
            'partner_id': vendor
        })
        customer_move = self.env['stock.move'].search([('group_id', '=', procurement_group.id)])
        manufacturing_order = self.env['mrp.production'].search([('product_id', '=', product.id)])
        self.assertTrue(manufacturing_order, 'No manufacturing order created.')

        # Check manufacturing order data.
        self.assertEqual(manufacturing_order.product_qty, 10, 'The manufacturing order qty should be the same as the move.')

        # Create procurement to decrease quantity in the initial move but not in the related MO.
        create_run_procurement(product, -5.00)
        self.assertEqual(customer_move.product_uom_qty, 5, 'The demand on the initial move should have been decreased when merged with the procurement.')
        self.assertEqual(manufacturing_order.product_qty, 10, 'The demand on the manufacturing order should not have been decreased.')

        # Create procurement to increase quantity on the initial move and should create a new MO for the missing qty.
        create_run_procurement(product, 2.00)
        self.assertEqual(customer_move.product_uom_qty, 5, 'The demand on the initial move should not have been increased since it should be a new move.')
        self.assertEqual(manufacturing_order.product_qty, 10, 'The demand on the initial manufacturing order should not have been increased.')
        manufacturing_orders = self.env['mrp.production'].search([('product_id', '=', product.id)])
        self.assertEqual(len(manufacturing_orders), 2, 'A new MO should have been created for missing demand.')
