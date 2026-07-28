# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import tagged, Form, HttpCase


@tagged('post_install', '-at_install')
class TestTourManualConsumption(HttpCase):
    def test_mrp_manual_consumption(self):
        """Test manual consumption mechanism. Test when manual consumption is
        True, quantity won't be updated automatically. Bom line with tracked
        products or operations should be set to manual consumption automatically.
        Also test that when manually change quantity, manual consumption
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
        self.assertEqual(move_nt.quantity, 5)
        self.assertTrue(move_nt.picked)
        self.assertEqual(move_sn.manual_consumption, True)
        self.assertEqual(move_sn.quantity, 5)
        self.assertFalse(move_sn.picked)
        self.assertEqual(move_lot.manual_consumption, True)
        self.assertEqual(move_lot.quantity, 5)
        self.assertFalse(move_lot.picked)

        action_id = self.env.ref('mrp.menu_mrp_production_action').action
        url = "/web#model=mrp.production&view_type=form&action=%s&id=%s" % (str(action_id.id), str(mo.id))
        self.start_tour(url, "test_mrp_manual_consumption", login="admin", timeout=100)

        self.assertEqual(move_nt.manual_consumption, True)
        self.assertEqual(move_nt.quantity, 6.0)
        self.assertEqual(move_sn.manual_consumption, True)
        self.assertEqual(move_sn.quantity, 0)
        self.assertEqual(move_lot.manual_consumption, True)
        self.assertEqual(move_lot.quantity, 0)

        backorder = mo.procurement_group_id.mrp_production_ids - mo
        move_nt = backorder.move_raw_ids.filtered(lambda m: m.product_id == product_nt)
        move_sn = backorder.move_raw_ids.filtered(lambda m: m.product_id == product_sn)
        move_lot = backorder.move_raw_ids.filtered(lambda m: m.product_id == product_lot)
        self.assertEqual(move_nt.manual_consumption, False)
        self.assertEqual(move_sn.manual_consumption, True)
        self.assertEqual(move_lot.manual_consumption, True)

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
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c1.id).mapped("quantity")), 4)
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c2.id).mapped("quantity")), 1)
        self.assertEqual(sorted(mo.move_raw_ids.mapped('picked')), sorted([False, True]))

        details_operation_form = Form(mo.move_raw_ids.filtered(lambda m: m.product_id == c1), view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.quantity = 4
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
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c1.id).mapped("quantity")), 4)
        self.assertEqual(sum(mo.move_raw_ids.filtered(lambda m: m.product_id.id == c2.id).mapped("quantity")), 1)

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

    def test_manual_consumption_with_different_component_price(self):
        """
        Test that the moves are merged correctly, even if the products have been used with different prices:
        - Create a product with a price of $10 and use it in a BoM with 1 unit.
        - Create a MO with this BoM and confirm it.
        - Update the price of the component to $20 and adjust the consumed quantity to 2.
        - Mark the MO as done.
        - Another move should be created and merged with the first move.

        """
        self.bom_4.consumption = 'warning'
        component = self.bom_4.bom_line_ids.product_id
        component.write({
            'type': 'product',
            'standard_price': 10,
        })
        self.env['stock.quant']._update_available_quantity(component, self.stock_location, 2)
        mo = self.env['mrp.production'].create({
            'product_qty': 1,
            'bom_id': self.bom_4.id,
        })
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        component.standard_price = 20
        mo.move_raw_ids.quantity = 2.0
        mo.move_raw_ids.picked = True
        mo.move_raw_ids.manual_consumption = True
        self.assertEqual(mo.state, 'progress')
        action = mo.button_mark_done()
        consumption_warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        action = consumption_warning.save().action_confirm()
        self.assertEqual(len(mo.move_raw_ids), 1)
        self.assertEqual(mo.move_raw_ids.quantity, 2)

    def test_update_manual_consumption_00(self):
        """
        Check that the manual consumption is set to true when the quantity is manualy set.
        """
        bom = self.bom_1
        components = bom.bom_line_ids.product_id
        self.env['stock.quant']._update_available_quantity(components[0], self.stock_location, 10)
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_qty = 4
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.move_raw_ids.mapped('manual_consumption'), [False, False])
        self.assertEqual(components[0].stock_quant_ids.reserved_quantity, 2.0)
        with Form(mo) as fmo:
            with fmo.move_raw_ids.edit(0) as line_0:
                line_0.quantity = 3.0
                line_0.picked = True
        self.assertEqual(mo.move_raw_ids.mapped('manual_consumption'), [True, False])
        self.assertEqual(components[0].stock_quant_ids.reserved_quantity, 3.0)
        mo.button_mark_done()
        self.assertRecordValues(mo.move_raw_ids, [{'quantity': 3.0, 'picked': True}, {'quantity': 4.0, 'picked': True}])

    def test_update_manual_consumption_01(self):
        """
        Check that the quantity of a raw line that is manually consumed is not updated
        when the qty producing is changed and that others are.
        """
        bom = self.bom_1
        components = bom.bom_line_ids.product_id
        self.env['stock.quant']._update_available_quantity(components[0], self.stock_location, 10)
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_qty = 4
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.move_raw_ids.mapped('manual_consumption'), [False, False])
        self.assertEqual(components[0].stock_quant_ids.reserved_quantity, 2.0)
        with Form(mo) as fmo:
            with fmo.move_raw_ids.edit(0) as line_0:
                line_0.quantity = 3.0
                line_0.picked = True
            fmo.qty_producing = 2.0
        self.assertEqual(mo.move_raw_ids.mapped('manual_consumption'), [True, False])
        self.assertEqual(components[0].stock_quant_ids.reserved_quantity, 3.0)
        self.assertRecordValues(mo.move_raw_ids, [{'quantity': 3.0, 'picked': True}, {'quantity': 2.0, 'picked': True}])

    def test_reservation_state_with_manual_consumption(self):
        """
        Check that the reservation state of an MO is not influenced by moves without demand.
        """
        self.warehouse_1.manufacture_steps = "pbm"
        bom = self.bom_1
        components = bom.bom_line_ids.mapped('product_id')
        components.type = "product"
        # make the second component optional
        bom.bom_line_ids[-1].product_qty = 0.0
        self.env['stock.quant']._update_available_quantity(components[0], self.warehouse_1.lot_stock_id, 10.0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.picking_type_id = self.warehouse_1.manu_type_id
        mo_form.bom_id = bom
        mo_form.product_qty = 4
        mo = mo_form.save()
        mo.action_confirm()
        self.assertRecordValues(mo.picking_ids.move_ids, [
            { "product_id": components[0].id, "product_uom_qty": 2.0}
        ])
        self.assertEqual(mo.reservation_state, "waiting")
        mo.picking_ids.button_validate()
        self.assertEqual(mo.reservation_state, "assigned")
        mo.move_raw_ids.filtered(lambda m: m.product_id == components[0]).picked = True
        self.assertEqual(mo.reservation_state, "assigned")
