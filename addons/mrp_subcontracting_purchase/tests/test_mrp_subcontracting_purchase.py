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
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
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
        self.assertEqual(receipt.move_ids.product_qty, product_qty, "Qty of subcontracted product to receive is incorrect")
        self.assertEqual(len(sub_mo), 1, "A subcontracting MO should have been created")
        self.assertEqual(sub_mo.product_qty, product_qty, "Qty of subcontracted product to produce is incorrect")

        # create a neg qty to proprogate to receipt
        lower_qty = product_qty - 1.0
        po.order_line.product_qty = lower_qty
        sub_mos = receipt._get_subcontract_production()
        self.assertEqual(receipt.move_ids.product_qty, lower_qty, "Qty of subcontracted product to receive should update (not validated yet)")
        self.assertEqual(len(sub_mos), 1, "Original subcontract MO should have absorbed qty change")
        self.assertEqual(sub_mo.product_qty, lower_qty, "Qty of subcontract MO should update (none validated yet)")

        # increase qty again
        po.order_line.product_qty = product_qty
        sub_mos = receipt._get_subcontract_production()
        self.assertEqual(sum(receipt.move_ids.mapped('product_qty')), product_qty, "Qty of subcontracted product to receive should update (not validated yet)")
        self.assertEqual(len(sub_mos), 1, "The subcontracted mo should have been updated")

        # check that a neg qty can't proprogate once receipt is done
        for move in receipt.move_ids:
            move.move_line_ids.qty_done = move.product_qty
        receipt.button_validate()
        self.assertEqual(receipt.state, 'done')
        self.assertEqual(sub_mos.state, 'done')
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
        receipt.move_ids.quantity_done = 10
        receipt.button_validate()

        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        return_wizard = return_form.save()
        return_wizard.product_return_moves.quantity = 3
        return_wizard.product_return_moves.to_refund = True
        return_id, _ = return_wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_ids.quantity_done = 3
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
        receipt.move_ids.quantity_done = 10
        receipt.button_validate()

        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        return_form.location_id = self.env.company.subcontracting_location_id
        return_wizard = return_form.save()
        return_wizard.product_return_moves.quantity = 3
        return_wizard.product_return_moves.to_refund = False
        return_id, _ = return_wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_ids.quantity_done = 3
        return_picking.button_validate()

        self.assertEqual(self.finished2.qty_available, 7.0)
        self.assertEqual(po.order_line.qty_received, 10.0)

    def test_orderpoint_warehouse_not_required(self):
        """
        The user creates a subcontracted bom for the product,
        then we create a po for the subcontracted bom we are gonna get
        orderpoints for the components without warehouse.Notice this is
        when our subcontracting location is also a replenish location.
        The test ensure that we can get those orderpoints without warehouse.
        """
        # Create a second warehouse to check which one will be used
        self.env['stock.warehouse'].create({'name': 'Second WH', 'code': 'WH02'})

        product = self.env['product.product'].create({
            'name': 'Product',
            'detailed_type': 'product',
        })
        component = self.env['product.product'].create({
            'name': 'Component',
            'detailed_type': 'product',
        })
        subcontractor = self.env['res.partner'].create({
            'name': 'Subcontractor',
            'property_stock_subcontractor': self.env.company.subcontracting_location_id.id,
        })
        self.env.company.subcontracting_location_id.replenish_location = True

        self.env['mrp.bom'].create({
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': product.uom_id.id,
            'type': 'subcontract',
            'subcontractor_ids': [(subcontractor.id)],
            'bom_line_ids': [(0, 0, {
                    'product_id': component.id,
                    'product_qty': 1,
                    'product_uom_id': component.uom_id.id,
            })],
        })

        po = self.env['purchase.order'].create({
            'partner_id': subcontractor.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_qty': 1,
                'product_uom': product.uom_id.id,
                'name': product.name,
                'price_unit': 1,
            })],
        })
        po.button_confirm()

        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', component.id)])
        self.assertTrue(orderpoint)
        self.assertEqual(orderpoint.warehouse_id, self.warehouse)

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
        receipt.move_ids.quantity_done = 10
        receipt.button_validate()

        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        wizard = return_form.save()
        wizard.product_return_moves.quantity = 1.0
        return_picking_id, _pick_type_id = wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_picking_id)
        return_picking.move_ids.quantity_done = 1.0
        return_picking.button_validate()

        pol = po.order_line
        pol.product_qty = 9.0

        stock_location_id = self.warehouse.lot_stock_id
        subco_location_id = self.env.company.subcontracting_location_id
        self.assertEqual(pol.qty_received, 9.0)
        self.assertEqual(pol.product_qty, 9.0)
        self.assertEqual(len(po.picking_ids), 2)
        self.assertRecordValues(po.picking_ids.move_ids, [
            {'location_dest_id': stock_location_id.id, 'quantity_done': 10.0, 'state': 'done'},
            {'location_dest_id': subco_location_id.id, 'quantity_done': 1.0, 'state': 'done'},
        ])
