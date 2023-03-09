# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import tagged, Form, HttpCase


@tagged('post_install', '-at_install')
class TestTourManualConsumption(HttpCase):
    def test_mrp_manual_consumption(self):
        """Test manual consumption mechanism. Test when manual consumption is
        True, quantity_done won't be updated automatically. Bom line with tracked
        products or operations should be set to manual consumption automatically.
        Also test that when manually change quantity_done, manual consumption
        will be set to True. Also test when create backorder, the manual consumption
        should be set according to the bom.
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
        product_sn = Product.create({
            'name': 'Serial',
            'type': 'product',
            'tracking': 'serial',})
        product_lot = Product.create({
            'name': 'Lot',
            'type': 'product',
            'tracking': 'lot',})
        bom = self.env['mrp.bom'].create({
            'product_id': product_finish.id,
            'product_tmpl_id': product_finish.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_nt.id, 'product_qty': 1}),
                (0, 0, {'product_id': product_sn.id, 'product_qty': 1}),
                (0, 0, {'product_id': product_lot.id, 'product_qty': 1}),
            ],
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_finish
        mo_form.bom_id = bom
        mo_form.product_qty = 10
        mo = mo_form.save()
        mo.action_confirm()
        mo.action_assign()

        # test no updating
        mo_form = Form(mo)
        mo_form.qty_producing = 5
        mo = mo_form.save()
        move_nt, move_sn, move_lot = mo.move_raw_ids
        self.assertEqual(move_nt.manual_consumption, False)
        self.assertEqual(move_nt.quantity_done, 5)
        self.assertEqual(move_sn.manual_consumption, True)
        self.assertEqual(move_sn.quantity_done, 0)
        self.assertEqual(move_lot.manual_consumption, True)
        self.assertEqual(move_lot.quantity_done, 0)

        action_id = self.env.ref('mrp.menu_mrp_production_action').action
        url = "/web#model=mrp.production&view_type=form&action=%s&id=%s" % (str(action_id.id), str(mo.id))
        self.start_tour(url, "test_mrp_manual_consumption", login="admin", timeout=200)

        self.assertEqual(move_nt.manual_consumption, True)
        self.assertEqual(move_nt.quantity_done, 6.0)
        self.assertEqual(move_sn.manual_consumption, True)
        self.assertEqual(move_sn.quantity_done, 0)
        self.assertEqual(move_lot.manual_consumption, True)
        self.assertEqual(move_lot.quantity_done, 0)

        backorder = mo.procurement_group_id.mrp_production_ids - mo
        move_nt = backorder.move_raw_ids.filtered(lambda m: m.product_id == product_nt)
        move_sn = backorder.move_raw_ids.filtered(lambda m: m.product_id == product_sn)
        move_lot = backorder.move_raw_ids.filtered(lambda m: m.product_id == product_lot)
        self.assertEqual(move_nt.manual_consumption, False)
        self.assertEqual(move_sn.manual_consumption, True)
        self.assertEqual(move_lot.manual_consumption, True)


class TestManualConsumption(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')

    def test_manual_consumption_backorder_00(self):
        """Test when use_auto_consume_components_lots is not set, manual consumption
        of the backorder is correctly set.
        """
        mo, _, _final, c1, c2 = self.generate_mo('none', 'lot', 'none', qty_final=2)

        self.assertTrue(mo.move_raw_ids.filtered(lambda m: m.product_id == c1).manual_consumption)
        self.assertFalse(mo.move_raw_ids.filtered(lambda m: m.product_id == c2).manual_consumption)

        lot = self.env['stock.lot'].create({
            'name': 'lot',
            'product_id': c1.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(c1, self.stock_location, 8, lot_id=lot)
        self.env['stock.quant']._update_available_quantity(c2, self.stock_location, 2)

        mo.action_assign()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo_form.save()
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c1.id).mapped("quantity_done")), 0)
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c2.id).mapped("quantity_done")), 1)

        details_operation_form = Form(mo.move_raw_ids.filtered(lambda m: m.product_id == c1), view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.qty_done = 4
            ml.lot_id = lot
        details_operation_form.save()

        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        backorder_mo = mo.procurement_group_id.mrp_production_ids[-1]

        self.assertTrue(backorder_mo.move_raw_ids.filtered(lambda m: m.product_id == c1).manual_consumption)
        self.assertFalse(backorder_mo.move_raw_ids.filtered(lambda m: m.product_id == c2).manual_consumption)

    def test_manual_consumption_backorder_01(self):
        """Test when use_auto_consume_components_lots is set, manual consumption
        of the backorder is correctly set.
        """
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')])[0]
        picking_type.use_auto_consume_components_lots = True

        mo, _, _final, c1, c2 = self.generate_mo('none', 'lot', 'none', qty_final=2)

        self.assertFalse(mo.move_raw_ids.filtered(lambda m: m.product_id == c1).manual_consumption)
        self.assertFalse(mo.move_raw_ids.filtered(lambda m: m.product_id == c2).manual_consumption)

        lot = self.env['stock.lot'].create({
            'name': 'lot',
            'product_id': c1.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(c1, self.stock_location, 8, lot_id=lot)
        self.env['stock.quant']._update_available_quantity(c2, self.stock_location, 2)

        mo.action_assign()
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo_form.save()
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c1.id).mapped("quantity_done")), 4)
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c2.id).mapped("quantity_done")), 1)

        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        backorder_mo = mo.procurement_group_id.mrp_production_ids[-1]

        self.assertFalse(backorder_mo.move_raw_ids.filtered(lambda m: m.product_id == c1).manual_consumption)
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
