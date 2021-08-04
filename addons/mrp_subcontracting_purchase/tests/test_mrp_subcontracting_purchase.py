# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

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
