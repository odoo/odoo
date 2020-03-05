# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

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
        self.assertEqual(production_product_6.state, 'confirmed', 'Production order should be for Confirmed state')

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
        })
        produce_product_4.action_assign()
        self.assertEqual(produce_product_4.product_qty, 8, "Wrong quantity of finish product.")
        self.assertEqual(produce_product_4.product_uom_id, self.uom_dozen, "Wrong quantity of finish product.")
        self.assertEqual(produce_product_4.reservation_state, 'assigned', "Consume material not available")

        # produce product4
        # ---------------

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': produce_product_4.id,
            'active_ids': [produce_product_4.id],
        }))
        produce_form.qty_producing = produce_product_4.product_qty
        product_produce = produce_form.save()
        product_produce.do_produce()
        produce_product_4.post_inventory()
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
        })
        production_product_6.action_assign()

        # ------------------------------------

        self.assertEqual(production_product_6.reservation_state, 'assigned', "Consume material not available")
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': production_product_6.id,
            'active_ids': [production_product_6.id],
        }))
        produce_form.qty_producing = production_product_6.product_qty
        product_produce = produce_form.save()
        product_produce.do_produce()
        production_product_6.post_inventory()
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
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': mo.id,
            'active_ids': [mo.id],
        }))
        produce_form.qty_producing = 3.0
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()
        self.assertEqual(mo.move_raw_ids.quantity_done, 3.0)
        picking_qc_to_stock.move_line_ids.qty_done = 5.0
        self.assertEqual(mo.move_raw_ids.reserved_availability, 5.0)
        self.assertEqual(mo.move_raw_ids.quantity_done, 3.0)

    def test_date_propagation(self):
        """ Check propagation of shedule date for manufaturing route."""

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
            'propagate_date': True,
            'propagate_date_minimum_delta': 1,
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

        self.assertAlmostEqual(mo.move_finished_ids.date_expected, mo.move_raw_ids.date_expected + timedelta(hours=1), delta=timedelta(seconds=1))

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

        move_dest_scheduled_date = move_dest.date_expected

        mo_form = Form(mo)
        mo_form.date_planned_start = fields.Datetime.to_datetime(mo_form.date_planned_start) + timedelta(days=5)
        mo_form.save()

        self.assertAlmostEqual(move_dest.date_expected, move_dest_scheduled_date + timedelta(days=5), delta=timedelta(seconds=1), msg='date is not propagated')

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
            'propagate_date': True,
            'propagate_date_minimum_delta': 1,
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

    def test_production_delay_alert(self):
        """Check if the delay alert is set to True on the stock move."""
        self.env['stock.rule'].search([]).delay_alert = True

        parent_product = self.env['product.template'].create({
            'name': 'Parent product',
            'route_ids': [
                (4, self.env.ref('mrp.route_warehouse0_manufacture').id, 0),
                (4, self.env.ref('stock.route_warehouse0_mto').id, 0)
            ]
        })
        child_product = self.env['product.template'].create({
            'name': 'Child product',
            'route_ids': [
                (4, self.env.ref('mrp.route_warehouse0_manufacture').id, 0),
                (4, self.env.ref('stock.route_warehouse0_mto').id, 0)
            ]
        })
        child_component = self.env['product.template'].create({
            'name': 'Child product',
        })
        parent_bom = self.env['mrp.bom'].create({
            'product_id': parent_product.product_variant_ids.id,
            'product_tmpl_id': parent_product.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'routing_id': self.routing_2.id,
            'type': 'normal',
        })
        self.env['mrp.bom.line'].create({
            'bom_id': parent_bom.id,
            'product_id': child_product.product_variant_ids.id,
            'product_qty': 2,
        })
        child_bom = self.env['mrp.bom'].create({
            'product_id': child_product.product_variant_ids.id,
            'product_tmpl_id': child_product.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'routing_id': self.routing_2.id,
            'type': 'normal',
        })
        self.env['mrp.bom.line'].create({
            'bom_id': child_bom.id,
            'product_id': child_component.product_variant_ids.id,
            'product_qty': 2,
        })

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = parent_product.product_variant_ids
        mrp_order = mrp_order_form.save()
        mrp_order.action_confirm()

        child_mrp_production = self.env['mrp.production'].search([('product_id', '=', child_product.product_variant_ids.id)])

        self.assertTrue(child_mrp_production.delay_alert)
        self.assertTrue(child_mrp_production.move_raw_ids.delay_alert)

    def test_procurement_with_empty_bom(self):
        """Ensure that a procurement request using a product with an empty BoM
        will create a MO in draft state that could be completed afterwards.
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
        self.assertEqual(production.state, 'draft')

        comp1 = self.env['product.product'].create({
            'name': 'egg',
        })
        move_values = production._get_move_raw_values(comp1, 40.0, self.env.ref('uom.product_uom_unit'))
        self.env['stock.move'].create(move_values)

        production.action_confirm()
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': production.id,
            'active_ids': [production.id],
        }))
        product_produce = produce_form.save()
        product_produce.do_produce()
        production.button_mark_done()

        move_dest._action_assign()
        self.assertEqual(move_dest.reserved_availability, 10.0)
