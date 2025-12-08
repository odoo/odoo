# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import Command
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
            'is_storable': True,
            'tracking': 'none',})
        product_nt = Product.create({
            'name': 'No tracking',
            'is_storable': True,
            'tracking': 'none',})
        bom = self.env['mrp.bom'].create({
            'product_id': product_finish.id,
            'product_tmpl_id': product_finish.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_nt.id, 'product_qty': 1}),
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
        self.assertEqual(move_nt.manual_consumption, False)
        self.assertEqual(move_nt.quantity, 0)
        self.assertFalse(move_nt.picked)

        url = f"/odoo/action-mrp.mrp_production_action/{mo.id}"
        self.start_tour(url, "test_mrp_manual_consumption_02", login="admin", timeout=100)

        self.assertEqual(move_nt.manual_consumption, True)
        self.assertEqual(move_nt.picked, True)
        self.assertEqual(move_nt.quantity, 16.0)

class TestManualConsumption(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({
            'implied_ids': [Command.link(cls.env.ref('stock.group_production_lot').id)],
        })

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
            'is_storable': True,
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

    def test_manual_consumption_quantity_change(self):
        """Test manual consumption mechanism.
        1. Test when a move is manual consumption but NOT picked, quantity will be updated automatically.
        2. Test when a move is manual consumption but IS picked, quantity will not be updated automatically.
        3. Test when create backorder, the manual consumption should be set according to the bom.
        """
        Product = self.env['product.product']
        product_finish = Product.create({
            'name': 'finish',
            'is_storable': True,
            'tracking': 'none'})
        product_auto_consumption = Product.create({
            'name': 'Automatic',
            'is_storable': True,
            'tracking': 'none'})
        product_manual_consumption = Product.create({
            'name': 'Manual',
            'is_storable': True,
            'tracking': 'none'})
        bom = self.env['mrp.bom'].create({
            'product_id': product_finish.id,
            'product_tmpl_id': product_finish.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_auto_consumption.id, 'product_qty': 1}),
                (0, 0, {'product_id': product_manual_consumption.id, 'product_qty': 1}),
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
        self.assertEqual(move_manual.manual_consumption, False)
        self.assertEqual(move_manual.quantity, 5)
        self.assertTrue(move_manual.picked)

        move_manual.quantity = 6
        move_manual._onchange_quantity()

        # Now we change quantity to 7. Automatic move will change quantity, but manual move will still be 5 because it has been already picked.
        mo_form = Form(mo)
        mo_form.qty_producing = 7
        mo = mo_form.save()

        self.assertEqual(move_auto.quantity, 7)
        self.assertEqual(move_manual.quantity, 6)

        # Bypass consumption issues wizard and create backorders
        action = mo.button_mark_done()
        warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        consumption = warning.save()
        action = consumption.action_set_qty()
        backorder_form = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder_form.save().action_backorder()
        backorder = mo.production_group_id.production_ids - mo

        # Check that backorders move have the same manual consumption values as BoM
        move_auto, move_manual = get_moves(backorder)
        self.assertEqual(move_auto.manual_consumption, False)
        self.assertEqual(move_manual.manual_consumption, False)

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
        components.is_storable = True
        # make the second component optional
        bom.bom_line_ids[-1].product_qty = 0.0
        self.env['stock.quant']._update_available_quantity(components[0], self.warehouse_1.lot_stock_id, 10.0)
        mo_form = Form(self.env['mrp.production'])
        mo_form.picking_type_id = self.picking_type_manu
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

    def test_no_consumption_when_quant_changed(self):
        """
        Test to ensure that from 'Details' wizard, changing only the lot or location
        of a component move line/quant (without changing the quantity) does not mark it as consumed.

        The wizard (opened via 'action_show_details' on move) should only set
        'manual_consumption' and 'picked' to True when the done quantity(quantity)
        differs from the demanded quantity(product_uom_qty).
        """
        bom = self.bom_4
        component = bom.bom_line_ids.product_id
        component.write({
            "is_storable": True,
            "tracking": "lot",
        })

        # Create two lots with quants.
        lots = self.env["stock.lot"].create([
            {"name": f"lot_{i}", "product_id": component.id} for i in range(2)
        ])
        for lot in lots:
            self.env["stock.quant"]._update_available_quantity(
                component, self.stock_location, 5, lot_id=lot
            )

        # Create and confirm a Manufacturing Order.
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()

        # Initially: not consumed.
        self.assertRecordValues(mo.move_raw_ids, [
            {"manual_consumption": False, "picked": False, "lot_ids": lots[0].ids},
        ])

        # Change only the lot in the 'Details' wizard, keep quantity unchanged.
        with Form.from_action(self.env, mo.move_raw_ids[0].action_show_details()) as wiz_form:
            with wiz_form.move_line_ids.edit(0) as move_line:
                move_line.lot_id = lots[1]
            wiz_form.save()

        # Still it should not consumed.
        self.assertRecordValues(mo.move_raw_ids, [
            {"manual_consumption": False, "picked": False, "lot_ids": lots[1].ids},
        ])

        # Change the quantity in the 'Details' wizard.
        with Form.from_action(self.env, mo.move_raw_ids[0].action_show_details()) as wiz_form:
            with wiz_form.move_line_ids.edit(0) as move_line:
                move_line.quantity = 2
            wiz_form.save()

        # Now it should be marked as consumed, since the done quantity differs from the demand.
        self.assertRecordValues(mo.move_raw_ids, [
            {"manual_consumption": True, "picked": True, "lot_ids": lots[1].ids},
        ])

    def test_manual_consumption_is_false_if_quantity_was_unchanged(self):
        """
        Check that a move's `manual_consumption` field is only set if the
        quantity of the move line was modified.
        """
        product_lot = self.env['product.product'].create({
            'name': 'Product Lot',
            'is_storable': True,
            'tracking': 'lot',
        })
        lot_1, lot_2 = self.env['stock.lot'].create([{
            'name': 'lot_1', 'product_id': product_lot.id,
        }, {
            'name': 'lot_2', 'product_id': product_lot.id,
        }])
        self.env['stock.quant']._update_available_quantity(product_lot, self.stock_location, 2, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(product_lot, self.stock_location, 2, lot_id=lot_2)

        # Create an MO with one component from lot_1, quantity 2
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_qty': 2,
            'move_raw_ids': [Command.create({
                'product_id': product_lot.id,
                'quantity': 2,
                'move_line_ids': [Command.create({
                    'product_id': product_lot.id,
                    'lot_id': lot_1.id,
                })],
            })],
        })

        # Using the details form, change only the lot of the move line
        action = mo.move_raw_ids.action_show_details()
        details_form = Form(mo.move_raw_ids.with_context(action['context']), view=action['view_id'])
        with details_form.move_line_ids.edit(0) as move_line:
            move_line.lot_id = lot_2
        move = details_form.save()
        # Since quantity was unchanged, `manual_consumption` should not be set
        self.assertFalse(move.manual_consumption)

        # Use the form again, this time changing the lot and the quantity
        with details_form.move_line_ids.edit(0) as move_line:
            move_line.lot_id = lot_1
            move_line.quantity = 1
        move = details_form.save()
        # Quantity was modified, so `manual_consumption` should be set
        self.assertTrue(move.manual_consumption)
