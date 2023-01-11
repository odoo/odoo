# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

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
