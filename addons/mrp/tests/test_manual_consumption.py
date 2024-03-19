# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import tagged, Form, HttpCase


@tagged('post_install', '-at_install')
class TestTourManualConsumption(HttpCase):
    def test_mrp_manual_consumption_02(self):
        """
        test that when a new quantity is manually set for a component,
        and the field picked is set to True,
        and the MO is marked as done, the component quantity is not overwritten.
        """
        Product = self.env['product.product']
        product_finish = Product.create({
            'name': 'finish',
            'type': 'product',
            'tracking': 'none',})
        product_nt = Product.create({
            'name': 'No tracking',
            'type': 'product',
            'tracking': 'none',})
        bom = self.env['mrp.bom'].create({
            'product_id': product_finish.id,
            'product_tmpl_id': product_finish.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_nt.id, 'product_qty': 1, 'manual_consumption': True}),
            ],
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_finish
        mo_form.bom_id = bom
        mo_form.product_qty = 10
        mo = mo_form.save()
        mo.action_confirm()

        self.assertEqual(mo.state, 'confirmed')
        move_nt = mo.move_raw_ids
        self.assertEqual(move_nt.manual_consumption, True)
        self.assertEqual(move_nt.quantity, 0)
        self.assertFalse(move_nt.picked)

        action_id = self.env.ref('mrp.menu_mrp_production_action').action
        url = "/web#model=mrp.production&view_type=form&action=%s&id=%s" % (str(action_id.id), str(mo.id))
        self.start_tour(url, "test_mrp_manual_consumption_02", login="admin", timeout=100)

        self.assertEqual(move_nt.manual_consumption, True)
        self.assertEqual(move_nt.picked, True)
        self.assertEqual(move_nt.quantity, 16.0)

class TestManualConsumption(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})

    def test_manual_consumption_backorder(self):
        """Test when use_auto_consume_components_lots is set, manual consumption
        of the backorder is correctly set.
        """
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')])[0]

        mo, _, _final, c1, c2 = self.generate_mo('none', 'lot', 'none', qty_final=2)

        self.assertTrue(mo.move_raw_ids.filtered(lambda m: m.product_id == c1).manual_consumption)
        self.assertFalse(mo.move_raw_ids.filtered(lambda m: m.product_id == c2).manual_consumption)

        lot = self.env['stock.lot'].create({
            'name': 'lot',
            'product_id': c1.id,
        })
        self.env['stock.quant']._update_available_quantity(c1, self.stock_location, 8, lot_id=lot)
        self.env['stock.quant']._update_available_quantity(c2, self.stock_location, 2)

        mo.action_assign()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo_form.save()
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c1.id).mapped("quantity")), 4)
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c2.id).mapped("quantity")), 1)

        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        backorder_mo = mo.procurement_group_id.mrp_production_ids[-1]

        self.assertTrue(backorder_mo.move_raw_ids.filtered(lambda m: m.product_id == c1).manual_consumption)
        self.assertFalse(backorder_mo.move_raw_ids.filtered(lambda m: m.product_id == c2).manual_consumption)

    def test_manual_consumption_split_merge_00(self):
        """Test manual consumption is correctly set after split or merge.
        """
        # Change 'Units' rounding to 1 (integer only quantities)
        self.uom_unit.rounding = 1
        # Create a mo for 10 products
        mo, _, _, p1, p2 = self.generate_mo('none', 'lot', 'none', qty_final=10)
        self.assertTrue(mo.move_raw_ids.filtered(lambda m: m.product_id == p1).manual_consumption)
        self.assertFalse(mo.move_raw_ids.filtered(lambda m: m.product_id == p2).manual_consumption)

        # Split in 3 parts
        action = mo.action_split()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.counter = 3
        action = wizard.save().action_split()
        for production in mo.procurement_group_id.mrp_production_ids:
            self.assertTrue(production.move_raw_ids.filtered(lambda m: m.product_id == p1).manual_consumption)
            self.assertFalse(production.move_raw_ids.filtered(lambda m: m.product_id == p2).manual_consumption)

        # Merge them back
        action = mo.procurement_group_id.mrp_production_ids.action_merge()
        mo = self.env[action['res_model']].browse(action['res_id'])
        self.assertTrue(mo.move_raw_ids.filtered(lambda m: m.product_id == p1).manual_consumption)
        self.assertFalse(mo.move_raw_ids.filtered(lambda m: m.product_id == p2).manual_consumption)

    def test_manual_consumption_quantity_change(self):
        """Test manual consumption mechanism.
        1. Test when a move is manual consumption but NOT picked, quantity will be updated automatically.
        2. Test when a move is manual consumption but IS picked, quantity will not be updated automatically.
        3. Test when create backorder, the manual consumption should be set according to the bom.
        """
        Product = self.env['product.product']
        product_finish = Product.create({
            'name': 'finish',
            'type': 'product',
            'tracking': 'none'})
        product_auto_consumption = Product.create({
            'name': 'Automatic',
            'type': 'product',
            'tracking': 'none'})
        product_manual_consumption = Product.create({
            'name': 'Manual',
            'type': 'product',
            'tracking': 'none'})
        bom = self.env['mrp.bom'].create({
            'product_id': product_finish.id,
            'product_tmpl_id': product_finish.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_auto_consumption.id, 'product_qty': 1}),
                (0, 0, {'product_id': product_manual_consumption.id, 'product_qty': 1, 'manual_consumption': True}),
            ],
        })

        def get_moves(mo):
            move_auto = mo.move_raw_ids.filtered(lambda m: m.product_id == product_auto_consumption)
            move_manual = mo.move_raw_ids.filtered(lambda m: m.product_id == product_manual_consumption)
            return move_auto, move_manual

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_finish
        mo_form.bom_id = bom
        mo_form.product_qty = 10
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()

        # After updating qty_producing, quantity changes for both moves, but manual move will remain not picked
        mo_form = Form(mo)
        mo_form.qty_producing = 5
        mo = mo_form.save()
        move_auto, move_manual = get_moves(mo)
        self.assertEqual(move_auto.manual_consumption, False)
        self.assertEqual(move_auto.quantity, 5)
        self.assertTrue(move_auto.picked)
        self.assertEqual(move_manual.manual_consumption, True)
        self.assertEqual(move_manual.quantity, 5)
        self.assertFalse(move_manual.picked)

        # Pick manual move
        move_manual.picked = True

        # Now we change quantity to 7. Automatic move will change quantity, but manual move will still be 5 because it has been already picked.
        mo_form = Form(mo)
        mo_form.qty_producing = 7
        mo = mo_form.save()

        self.assertEqual(move_auto.quantity, 7)
        self.assertEqual(move_manual.quantity, 5)

        # Bypass consumption issues wizard and create backorders
        action = mo.button_mark_done()
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        consumption = warning.save()
        action = consumption.action_set_qty()
        backorder_form = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder_form.save().action_backorder()
        backorder = mo.procurement_group_id.mrp_production_ids - mo

        # Check that backorders move have the same manual consumption values as BoM
        move_auto, move_manual = get_moves(backorder)
        self.assertEqual(move_auto.manual_consumption, False)
        self.assertEqual(move_manual.manual_consumption, True)
