# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class MrpSubcontractingPurchaseTest(TestMrpSubcontractingCommon):

    def setUp(self):
        super().setUp()
        self.finished2, self.comp3 = self.env['product.product'].create([{
            'name': 'SuperProduct',
            'type': 'product',
        }, {
            'name': 'Component',
            'type': 'consu',
        }])
        self.vendor = self.env['res.partner'].create({
            'name': 'Vendor',
            'company_id': self.env.ref('base.main_company').id,
        })

        self.bom_finished2 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.finished2.product_tmpl_id.id,
            'type': 'subcontract',
            'subcontractor_ids': [(6, 0, self.subcontractor_partner1.ids)],
            'bom_line_ids': [(0, 0, {
                'product_id': self.comp3.id,
                'product_qty': 1,
            })],
        })

    def test_count_smart_buttons(self):
        resupply_sub_on_order_route = self.env['stock.location.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({'route_ids': [Command.link(resupply_sub_on_order_route.id)]})

        # I create a draft Purchase Order for first in move for 10 kg at 50 euro
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [Command.create({
                'name': 'finished',
                'product_id': self.finished.id,
                'product_qty': 1.0,
                'product_uom': self.finished.uom_id.id,
                'price_unit': 50.0}
            )],
        })

        po.button_confirm()

        self.assertEqual(po.subcontracting_resupply_picking_count, 1)
        action1 = po.action_view_subcontracting_resupply()
        picking = self.env[action1['res_model']].browse(action1['res_id'])
        self.assertEqual(picking.subcontracting_source_purchase_count, 1)
        action2 = picking.action_view_subcontracting_source_purchase()
        po_action2 = self.env[action2['res_model']].browse(action2['res_id'])
        self.assertEqual(po_action2, po)

    def test_decrease_qty(self):
        """ Tests when a PO for a subcontracted product has its qty decreased after confirmation
        """

        product_qty = 5.0
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [Command.create({
                'name': 'finished',
                'product_id': self.finished.id,
                'product_qty': product_qty,
                'product_uom': self.finished.uom_id.id,
                'price_unit': 50.0}
            )],
        })

        po.button_confirm()
        receipt = po.picking_ids
        sub_mo = receipt._get_subcontract_production()
        self.assertEqual(len(receipt), 1, "A receipt should have been created")
        self.assertEqual(receipt.move_lines.product_qty, product_qty, "Qty of subcontracted product to receive is incorrect")
        self.assertEqual(len(sub_mo), 1, "A subcontracting MO should have been created")
        self.assertEqual(sub_mo.product_qty, product_qty, "Qty of subcontracted product to produce is incorrect")

        # create a neg qty to proprogate to receipt
        lower_qty = product_qty - 1.0
        po.order_line.product_qty = lower_qty
        sub_mos = receipt._get_subcontract_production()
        self.assertEqual(receipt.move_lines.product_qty, lower_qty, "Qty of subcontracted product to receive should update (not validated yet)")
        self.assertEqual(len(sub_mos), 1, "Original subcontract MO should have absorbed qty change")
        self.assertEqual(sub_mo.product_qty, lower_qty, "Qty of subcontract MO should update (none validated yet)")

        # increase qty again
        po.order_line.product_qty = product_qty
        sub_mos = receipt._get_subcontract_production()
        self.assertEqual(sum(receipt.move_lines.mapped('product_qty')), product_qty, "Qty of subcontracted product to receive should update (not validated yet)")
        self.assertEqual(len(sub_mos), 2, "A new subcontracting MO should have been created")

        # check that a neg qty can't proprogate once receipt is done
        for move in receipt.move_lines:
            move.move_line_ids.qty_done = move.product_qty
        receipt.button_validate()
        self.assertEqual(receipt.state, 'done')
        self.assertEqual(sub_mos[0].state, 'done')
        self.assertEqual(sub_mos[1].state, 'done')
        with self.assertRaises(UserError):
            po.order_line.product_qty = lower_qty

    def test_purchase_and_return01(self):
        """
        The user buys 10 x a subcontracted product P. He receives the 10
        products and then does a return with 3 x P. The test ensures that the
        final received quantity is correctly computed
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [(0, 0, {
                'name': self.finished2.name,
                'product_id': self.finished2.id,
                'product_uom_qty': 10,
                'product_uom': self.finished2.uom_id.id,
                'price_unit': 1,
            })],
        })
        po.button_confirm()

        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom_finished2.id)])
        self.assertTrue(mo)

        receipt = po.picking_ids
        receipt.move_lines.quantity_done = 10
        receipt.button_validate()

        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = 3
            line.to_refund = True
        return_wizard = return_form.save()
        return_id, _ = return_wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_lines.quantity_done = 3
        return_picking.button_validate()

        self.assertEqual(self.finished2.qty_available, 7.0)
        self.assertEqual(po.order_line.qty_received, 7.0)

    def test_purchase_and_return02(self):
        """
        The user buys 10 x a subcontracted product P. He receives the 10
        products and then does a return with 3 x P (with the flag to_refund
        disabled and the subcontracting location as return location). The test
        ensures that the final received quantity is correctly computed
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})

        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [(0, 0, {
                'name': self.finished2.name,
                'product_id': self.finished2.id,
                'product_uom_qty': 10,
                'product_uom': self.finished2.uom_id.id,
                'price_unit': 1,
            })],
        })
        po.button_confirm()

        mo = self.env['mrp.production'].search([('bom_id', '=', self.bom_finished2.id)])
        self.assertTrue(mo)

        receipt = po.picking_ids
        receipt.move_lines.quantity_done = 10
        receipt.button_validate()

        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        return_form.location_id = self.env.company.subcontracting_location_id
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = 3
            line.to_refund = False
        return_wizard = return_form.save()
        return_id, _ = return_wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_lines.quantity_done = 3
        return_picking.button_validate()

        self.assertEqual(self.finished2.qty_available, 7.0)
        self.assertEqual(po.order_line.qty_received, 10.0)

    def test_purchase_and_return03(self):
        """
        With 2 steps receipt and an input location child of Physical Location (instead of WH)
        The user buys 10 x a subcontracted product P. He receives the 10
        products and then does a return with 3 x P. The test ensures that the
        final received quantity is correctly computed
        """
        # Set 2 steps receipt
        self.warehouse.write({"reception_steps": "two_steps"})
        # Set 'Input' parent location to 'Physical locations'
        physical_locations = self.env.ref("stock.stock_location_locations")
        input_location = self.warehouse.wh_input_stock_loc_id
        input_location.write({"location_id": physical_locations.id})

        # Create Purchase
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [(0, 0, {
                'name': self.finished2.name,
                'product_id': self.finished2.id,
                'product_uom_qty': 10,
                'product_uom': self.finished2.uom_id.id,
                'price_unit': 1,
            })],
        })
        po.button_confirm()

        # Receive Products
        receipt = po.picking_ids
        receipt.move_lines.quantity_done = 10
        receipt.button_validate()

        self.assertEqual(po.order_line.qty_received, 10.0)

        # Return Products
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        with return_form.product_return_moves.edit(0) as line:
            line.quantity = 3
            line.to_refund = True
        return_wizard = return_form.save()
        return_id, _ = return_wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_lines.quantity_done = 3
        return_picking.button_validate()

        self.assertEqual(po.order_line.qty_received, 7.0)

    def test_return_and_decrease_pol_qty(self):
        """
        Buy and receive 10 subcontracted products. Return one. Then adapt the
        demand on the PO to 9.
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [(0, 0, {
                'name': self.finished2.name,
                'product_id': self.finished2.id,
                'product_qty': 10,
                'product_uom': self.finished2.uom_id.id,
                'price_unit': 1,
            })],
        })
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_lines.quantity_done = 10
        receipt.button_validate()

        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        wizard = return_form.save()
        wizard.product_return_moves.quantity = 1.0
        return_picking_id, _pick_type_id = wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_picking_id)
        return_picking.move_lines.quantity_done = 1.0
        return_picking.button_validate()

        pol = po.order_line
        pol.product_qty = 9.0

        stock_location_id = self.warehouse.lot_stock_id
        subco_location_id = self.env.company.subcontracting_location_id
        self.assertEqual(pol.qty_received, 9.0)
        self.assertEqual(pol.product_qty, 9.0)
        self.assertEqual(len(po.picking_ids), 2)
        self.assertRecordValues(po.picking_ids.move_lines, [
            {'location_dest_id': stock_location_id.id, 'quantity_done': 10.0, 'state': 'done'},
            {'location_dest_id': subco_location_id.id, 'quantity_done': 1.0, 'state': 'done'},
        ])

    def test_resupply_order_buy_mto(self):
        """ Test a subcontract component can has resupply on order + buy + mto route"""
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        resupply_sub_on_order_route = self.env['stock.location.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({
             'route_ids': [
                Command.link(resupply_sub_on_order_route.id),
                Command.link(self.env.ref('purchase_stock.route_warehouse0_buy').id),
                Command.link(mto_route.id)],
             'seller_ids': [Command.create({
                 'name': self.vendor.id,
             })],
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [Command.create({
                'name': 'finished',
                'product_id': self.finished.id,
                'product_qty': 1.0,
                'product_uom': self.finished.uom_id.id,
                'price_unit': 50.0}
            )],
        })

        po.button_confirm()
        ressuply_pick = self.env['stock.picking'].search([('location_dest_id', '=', self.env.company.subcontracting_location_id.id)])
        self.assertEqual(len(ressuply_pick.move_lines), 2)
        self.assertEqual(ressuply_pick.move_lines.mapped('product_id'), self.comp1 | self.comp2)

        # should have create a purchase order for the components
        comp_po = self.env['purchase.order'].search([('partner_id', '=', self.vendor.id)])
        self.assertEqual(len(comp_po.order_line), 2)
        self.assertEqual(comp_po.order_line.mapped('product_id'), self.comp1 | self.comp2)
        # confirm the po should create stock moves linked to the resupply
        comp_po.button_confirm()
        comp_receipt = comp_po.picking_ids
        self.assertEqual(comp_receipt.move_lines.move_dest_ids, ressuply_pick.move_lines)

        # validate the comp receipt should reserve the resupply
        self.assertEqual(ressuply_pick.state, 'waiting')
        comp_receipt.move_lines.quantity_done = 1
        comp_receipt.button_validate()
        self.assertEqual(ressuply_pick.state, 'assigned')
