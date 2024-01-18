# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command
from odoo.exceptions import UserError
from odoo.fields import Date
from odoo.tests import Form, tagged, loaded_demo_data

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
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
            move.move_line_ids.quantity = move.product_qty
        receipt.move_ids.picked = True
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
        receipt.move_ids.quantity = 10
        receipt.move_ids.picked = True
        receipt.button_validate()

        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        return_wizard = return_form.save()
        return_wizard.product_return_moves.quantity = 3
        return_wizard.product_return_moves.to_refund = True
        return_id, _ = return_wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_ids.quantity = 3
        return_picking.move_ids.picked = True
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
        receipt.move_ids.quantity = 10
        receipt.move_ids.picked = True
        receipt.button_validate()

        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        return_form.location_id = self.env.company.subcontracting_location_id
        return_wizard = return_form.save()
        return_wizard.product_return_moves.quantity = 3
        return_wizard.product_return_moves.to_refund = False
        return_id, _ = return_wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_ids.quantity = 3
        return_picking.move_ids.picked = True
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
        receipt.move_ids.quantity = 10
        receipt.move_ids.picked = True
        receipt.button_validate()

        self.assertEqual(po.order_line.qty_received, 10.0)

        # Return Products
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        return_wizard = return_form.save()
        return_wizard.product_return_moves.quantity = 3
        return_wizard.product_return_moves.to_refund = True
        return_id, _ = return_wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_id)
        return_picking.move_ids.quantity = 3
        return_picking.move_ids.picked = True
        return_picking.button_validate()

        self.assertEqual(po.order_line.qty_received, 7.0)

    def test_subcontracting_resupply_price_diff(self):
        """Test that the price difference is correctly computed when a subcontracted
        product is resupplied.
        """
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({'route_ids': [(6, None, [resupply_sub_on_order_route.id])]})
        product_category_all = self.env.ref('product.product_category_all')
        product_category_all.property_cost_method = 'standard'
        product_category_all.property_valuation = 'real_time'

        stock_price_diff_acc_id = self.env['account.account'].create({
            'name': 'default_account_stock_price_diff',
            'code': 'STOCKDIFF',
            'reconcile': True,
            'account_type': 'asset_current',
            'company_id': self.env.company.id,
        })
        product_category_all.property_account_creditor_price_difference_categ = stock_price_diff_acc_id

        self.comp1.standard_price = 10.0
        self.comp2.standard_price = 20.0
        self.finished.standard_price = 100

        # Create a PO for 1 finished product.
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.subcontractor_partner1
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.finished
            po_line.product_qty = 1
            po_line.price_unit = 50   # should be 70
        po = po_form.save()
        po.button_confirm()

        action = po.action_view_subcontracting_resupply()
        resupply_picking = self.env[action['res_model']].browse(action['res_id'])
        resupply_picking.move_ids.quantity = 1
        resupply_picking.move_ids.picked = True
        resupply_picking.button_validate()

        action = po.action_view_picking()
        final_picking = self.env[action['res_model']].browse(action['res_id'])
        final_picking.move_ids.quantity = 1
        final_picking.move_ids.picked = True
        final_picking.button_validate()

        action = po.action_create_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        invoice.invoice_date = Date.today()
        invoice.action_post()

        # price diff line should be 100 - 50 - 10 - 20
        price_diff_line = invoice.line_ids.filtered(lambda m: m.account_id == stock_price_diff_acc_id)
        self.assertEqual(price_diff_line.credit, 20)

    def test_subcontract_product_price_change(self):
        """ Create a PO for subcontracted product, receive the product (finish MO),
            create vendor bill and edit the product price, confirm the bill.
            An extra SVL should be created to correct the valuation of the product
            Also check account move data for real time inventory
        """
        product_category_all = self.env.ref('product.product_category_all')
        product_category_all.property_cost_method = 'fifo'
        product_category_all.property_valuation = 'real_time'
        in_account = self.env['account.account'].create({
            'name': 'IN Account',
            'code': '000001',
            'account_type': 'asset_current',
        })
        out_account = self.env['account.account'].create({
            'name': 'OUT Account',
            'code': '000002',
            'account_type': 'asset_current',
        })
        valu_account = self.env['account.account'].create({
            'name': 'VALU Account',
            'code': '000003',
            'account_type': 'asset_current',
        })
        production_cost_account = self.env['account.account'].create({
            'name': 'PROD COST Account',
            'code': '000004',
            'account_type': 'asset_current',
        })
        product_category_all.property_stock_account_input_categ_id = in_account
        product_category_all.property_stock_account_output_categ_id = out_account
        product_category_all.property_stock_account_production_cost_id = production_cost_account
        product_category_all.property_stock_valuation_account_id = valu_account
        stock_in_acc_id = product_category_all.property_stock_account_input_categ_id.id
        self.comp1.standard_price = 8
        purchase = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [Command.create({
                'name': self.finished.name,
                'product_id': self.finished.id,
                'product_qty': 10,
                'product_uom': self.finished.uom_id.id,
                'price_unit': 1,
            })],
        })
        purchase.button_confirm()
        # receive product
        receipt = purchase.picking_ids
        receipt.move_ids.picked = True
        receipt.button_validate()
        # create bill
        purchase.action_create_invoice()
        aml = self.env['account.move.line'].search([('purchase_line_id', '=', purchase.order_line.id)])
        # add 0.5 per unit ( 0.5 x 10 ) = 5 extra valuation
        aml.price_unit = 1.5
        aml.move_id.invoice_date = Date.today()
        aml.move_id.action_post()
        svl = aml.stock_valuation_layer_ids
        self.assertEqual(len(svl), 1)
        self.assertEqual(svl.value, 5)
        self.assertEqual(self.finished.standard_price, 1.5 + 8, 'product cost should match vendor subcontracting cost + component cost')
        # check for the automated inventory valuation
        account_move_credit_line = svl.account_move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(account_move_credit_line.account_id.id, stock_in_acc_id)
        self.assertEqual(account_move_credit_line.credit, 5)

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
        receipt.move_ids.quantity = 10
        receipt.button_validate()

        return_form = Form(self.env['stock.return.picking'].with_context(active_id=receipt.id, active_model='stock.picking'))
        wizard = return_form.save()
        wizard.product_return_moves.quantity = 1.0
        return_picking_id, _pick_type_id = wizard._create_returns()

        return_picking = self.env['stock.picking'].browse(return_picking_id)
        return_picking.move_ids.quantity = 1.0
        return_picking.button_validate()

        pol = po.order_line
        pol.product_qty = 9.0

        stock_location_id = self.warehouse.lot_stock_id
        subco_location_id = self.env.company.subcontracting_location_id
        self.assertEqual(pol.qty_received, 9.0)
        self.assertEqual(pol.product_qty, 9.0)
        self.assertEqual(len(po.picking_ids), 2)
        self.assertRecordValues(po.picking_ids.move_ids, [
            {'location_dest_id': stock_location_id.id, 'quantity': 10.0, 'state': 'done'},
            {'location_dest_id': subco_location_id.id, 'quantity': 1.0, 'state': 'done'},
        ])

    def test_subcontracting_lead_days(self):
        """ Test the lead days computation for subcontracting. Subcontracting delay =
            max(Vendor lead time, Manufacturing lead time + DTPMO) + Days to Purchase + Purchase security lead time
        """
        rule = self.env['stock.rule'].search([('action', '=', 'buy')], limit=1)
        self.env.company.manufacturing_lead = 114514   # should never be used

        self.env.company.po_lead = 1
        self.env.company.days_to_purchase = 2
        # Case 1 Vendor lead time >= Manufacturing lead time + DTPMO
        seller = self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.finished.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 12.0,
            'delay': 10
        })
        self.bom.produce_delay = 3
        self.bom.days_to_prepare_mo = 4
        delays, _ = rule._get_lead_days(self.finished, supplierinfo=seller)
        self.assertEqual(delays['total_delay'], seller.delay + self.env.company.po_lead + self.env.company.days_to_purchase)
        # Case 2 Vendor lead time < Manufacturing lead time + DTPMO
        self.bom.produce_delay = 5
        self.bom.days_to_prepare_mo = 6
        delays, _ = rule._get_lead_days(self.finished, supplierinfo=seller)
        self.assertEqual(delays['total_delay'], self.bom.produce_delay + self.bom.days_to_prepare_mo + self.env.company.po_lead + self.env.company.days_to_purchase)

    def test_subcontracting_lead_days_on_overview(self):
        """Test on the BOM overview, the lead days and resupply availability are
        correctly computed. The dtpmo on the bom should be used for the lead days,
        while the resupply availability should be based on the calculated dtpmo.
        """
        # should never be used
        self.env.company.manufacturing_lead = 114514
        # should be added in all cases
        self.env.company.po_lead = 5
        self.env.company.days_to_purchase = 5

        rule = self.env['stock.rule'].search([('action', '=', 'buy')], limit=1)
        (self.finished | self.comp1 | self.comp2).route_ids = [(6, None, [rule.route_id.id])]
        self.comp2_bom.active = False
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.finished.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 648.0,
            'delay': 15
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp1.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 648.0,
            'delay': 10
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp2.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 648.0,
            'delay': 6
        })
        self.bom.produce_delay = 10
        self.bom.days_to_prepare_mo = 0

        # Case 1: Vendor lead time >= Manufacturing lead time + DTPMO on BOM
        bom_data = self.env['report.mrp.report_bom_structure']._get_bom_data(self.bom, self.warehouse, self.finished)
        self.assertEqual(bom_data['lead_time'], 15 + 5 + 5 + 0,
            "Lead time = Purchase lead time(finished) + Days to Purchase + Purchase security lead time + DTPMO on BOM")
        self.assertEqual(bom_data['resupply_avail_delay'], 10 + 5 + 5 + 20,
            "Component avail delay = Purchase lead time(comp1) + Days to Purchase + Purchase security lead time + Calculated DTPMO")

        # Case 2: Vendor lead time < Manufacturing lead time + DTPMO on BOM
        self.bom.action_compute_bom_days()
        self.assertEqual(self.bom.days_to_prepare_mo, 10 + 5 + 5,
            "DTPMO = Purchase lead time(comp1) + Days to Purchase + Purchase security lead time")
        self.bom.days_to_prepare_mo = 10
        bom_data = self.env['report.mrp.report_bom_structure']._get_bom_data(self.bom, self.warehouse, self.finished)
        self.assertEqual(bom_data['lead_time'], 10 + 5 + 5 + 10,
            "Lead time = Manufacturing lead time + Days to Purchase + Purchase security lead time + DTPMO on BOM")
        self.assertEqual(bom_data['resupply_avail_delay'], 10 + 5 + 5 + 20,
            "Component avail delay = Manufacturing lead time + Days to Purchase + Purchase security lead time + Calculated DTPMO")

        # Update stock for components, calculate DTPMO should be 0
        self.env['stock.quant']._update_available_quantity(self.comp1, self.warehouse.lot_stock_id, 100)
        self.env['stock.quant']._update_available_quantity(self.comp2, self.warehouse.lot_stock_id, 100)
        self.env.invalidate_all()   # invalidate cache to get updated qty_available
        # Case 1: Vendor lead time >= Manufacturing lead time + DTPMO on BOM
        self.bom.days_to_prepare_mo = 2
        bom_data = self.env['report.mrp.report_bom_structure']._get_bom_data(self.bom, self.warehouse, self.finished)
        self.assertEqual(bom_data['lead_time'], 15 + 5 + 5,
            "Lead time = Purchase lead time(finished) + Days to Purchase + Purchase security lead time")
        for component in bom_data['components']:
            self.assertEqual(component['availability_state'], 'available')
        # Case 2: Vendor lead time < Manufacturing lead time + DTPMO on BOM
        self.bom.action_compute_bom_days()
        self.assertEqual(self.bom.days_to_prepare_mo, 10 + 5 + 5,
            "DTPMO = Purchase lead time(comp1) + Days to Purchase + Purchase security lead time")
        bom_data = self.env['report.mrp.report_bom_structure']._get_bom_data(self.bom, self.warehouse, self.finished)
        self.assertEqual(bom_data['lead_time'], 10 + 5 + 5 + 20,
            "Lead time = Manufacturing lead time + Days to Purchase + Purchase security lead time + DTPMO on BOM")
        for component in bom_data['components']:
            self.assertEqual(component['availability_state'], 'available')

    def test_resupply_order_buy_mto(self):
        """ Test a subcontract component can has resupply on order + buy + mto route"""
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({
             'route_ids': [
                Command.link(resupply_sub_on_order_route.id),
                Command.link(self.env.ref('purchase_stock.route_warehouse0_buy').id),
                Command.link(mto_route.id)],
             'seller_ids': [Command.create({
                 'partner_id': self.vendor.id,
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
        self.assertEqual(len(ressuply_pick.move_ids), 2)
        self.assertEqual(ressuply_pick.move_ids.mapped('product_id'), self.comp1 | self.comp2)

        # should have create a purchase order for the components
        comp_po = self.env['purchase.order'].search([('partner_id', '=', self.vendor.id)])
        self.assertEqual(len(comp_po.order_line), 2)
        self.assertEqual(comp_po.order_line.mapped('product_id'), self.comp1 | self.comp2)
        # confirm the po should create stock moves linked to the resupply
        comp_po.button_confirm()
        comp_receipt = comp_po.picking_ids
        self.assertEqual(comp_receipt.move_ids.move_dest_ids, ressuply_pick.move_ids)

        # validate the comp receipt should reserve the resupply
        self.assertEqual(ressuply_pick.state, 'waiting')
        comp_receipt.move_ids.quantity = 1
        comp_receipt.move_ids.picked = True
        comp_receipt.button_validate()
        self.assertEqual(ressuply_pick.state, 'assigned')

    def test_update_qty_purchased_with_subcontracted_product(self):
        """
        Test That we can update the quantity of a purchase order line with a subcontracted product
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [Command.create({
                'name': 'finished',
                'product_id': self.finished.id,
                'product_qty': 3.0,
                'product_uom': self.finished.uom_id.id,
                'price_unit': 50.0}
            )],
        })
        po.button_confirm()
        self.assertEqual(len(po.picking_ids), 1)
        picking = po.picking_ids
        picking.move_ids.quantity = 2.0
        # When we validate the picking manually, we create a backorder.
        backorder_wizard_dict = picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()
        self.assertEqual(len(po.picking_ids), 2)
        picking.backorder_ids.action_cancel()
        self.assertEqual(picking.backorder_ids.state, 'cancel')
        po.order_line.product_qty = 2.0
        self.assertEqual(po.order_line.product_qty, 2.0)
