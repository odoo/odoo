# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import UserError

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class MrpSubcontractingPurchaseTest(TestMrpSubcontractingCommon):

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
