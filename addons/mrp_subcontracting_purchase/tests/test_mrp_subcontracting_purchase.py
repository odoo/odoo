# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from datetime import datetime, timedelta
from freezegun import freeze_time
from json import loads

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
            'is_storable': True,
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

    @freeze_time('2024-01-01')
    def test_bom_overview_availability(self):
        # Create routes for components and the main product
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.finished.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 1.0,
            'delay': 10
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp1.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 648.0,
            'delay': 5
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp2.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'price': 648.0,
            'delay': 5
        })

        self.bom.produce_delay = 1
        self.bom.days_to_prepare_mo = 3

        # Add 4 units of each component to subcontractor's location
        subcontractor_location = self.env.company.subcontracting_location_id
        self.env['stock.quant']._update_available_quantity(self.comp1, subcontractor_location, 4)
        self.env['stock.quant']._update_available_quantity(self.comp2, subcontractor_location, 4)

        # Generate a report for 3 products: all products should be ready for production
        bom_data = self.env['report.mrp.report_bom_structure']._get_report_data(self.bom.id, 3)

        self.assertTrue(bom_data['lines']['components_available'])
        for component in bom_data['lines']['components']:
            self.assertEqual(component['quantity_on_hand'], 4)
            self.assertEqual(component['availability_state'], 'available')
        self.assertEqual(bom_data['lines']['earliest_capacity'], 3)
        self.assertEqual(bom_data['lines']['earliest_date'], '01/11/2024')
        self.assertTrue('leftover_capacity' not in bom_data['lines']['earliest_date'])
        self.assertTrue('leftover_date' not in bom_data['lines']['earliest_date'])

        # Generate a report for 5 products: only 4 products should be ready for production
        bom_data = self.env['report.mrp.report_bom_structure']._get_report_data(self.bom.id, 5)

        self.assertFalse(bom_data['lines']['components_available'])
        for component in bom_data['lines']['components']:
            self.assertEqual(component['quantity_on_hand'], 4)
            self.assertEqual(component['availability_state'], 'estimated')
        self.assertEqual(bom_data['lines']['earliest_capacity'], 4)
        self.assertEqual(bom_data['lines']['earliest_date'], '01/11/2024')
        self.assertEqual(bom_data['lines']['leftover_capacity'], 1)
        self.assertEqual(bom_data['lines']['leftover_date'], '01/16/2024')

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
                'product_uom_id': self.finished.uom_id.id,
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
                'product_uom_id': self.finished.uom_id.id,
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
                'product_uom_id': self.finished2.uom_id.id,
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
        return_picking = return_wizard._create_return()
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
        self.env.user.write({'group_ids': [(4, grp_multi_loc.id)]})

        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [(0, 0, {
                'name': self.finished2.name,
                'product_id': self.finished2.id,
                'product_uom_qty': 10,
                'product_uom_id': self.finished2.uom_id.id,
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
        return_wizard.product_return_moves.to_refund = False
        return_picking = return_wizard._create_return()
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
            'is_storable': True,
        })
        component = self.env['product.product'].create({
            'name': 'Component',
            'is_storable': True,
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
                'product_uom_id': product.uom_id.id,
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
                'product_uom_id': self.finished2.uom_id.id,
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
        return_picking = return_wizard._create_return()
        return_picking.move_ids.quantity = 3
        return_picking.move_ids.picked = True
        return_picking.button_validate()

        self.assertEqual(po.order_line.qty_received, 7.0)

    def test_subcontracting_resupply_price_diff(self):
        """Test that the price difference is correctly computed when a subcontracted
        product is resupplied.
        """
        self.env.company.anglo_saxon_accounting = True
        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({'route_ids': [(6, None, [resupply_sub_on_order_route.id])]})
        product_category_all = self.product_category
        product_category_all.property_cost_method = 'standard'
        product_category_all.property_valuation = 'real_time'
        self._setup_category_stock_journals()

        stock_price_diff_acc_id = self.env['account.account'].create({
            'name': 'default_account_stock_price_diff',
            'code': 'STOCKDIFF',
            'reconcile': True,
            'account_type': 'asset_current',
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
            po_line.product_qty = 2
            po_line.price_unit = 50   # should be 70
        po = po_form.save()
        po.button_confirm()

        action = po.action_view_subcontracting_resupply()
        resupply_picking = self.env[action['res_model']].browse(action['res_id'])
        resupply_picking.move_ids.quantity = 2
        resupply_picking.move_ids.picked = True
        resupply_picking.button_validate()

        action = po.action_view_picking()
        final_picking = self.env[action['res_model']].browse(action['res_id'])
        final_picking.move_ids.quantity = 2
        final_picking.move_ids.picked = True
        final_picking.button_validate()

        action = po.action_create_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        invoice.invoice_date = Date.today()
        invoice.invoice_line_ids.quantity = 1
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
        product_category_all = self.product_category
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

        resupply_sub_on_order_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        (self.comp1 + self.comp2).write({'route_ids': [Command.link(resupply_sub_on_order_route.id)]})
        purchase_comps = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,  # can be any partner
            'order_line': [
                Command.create({
                    'name': self.comp1.name,
                    'product_id': self.comp1.id,
                    'product_uom_qty': 1,
                    'product_uom_id': self.finished.uom_id.id,
                    'price_unit': 10,
                }),
                Command.create({
                    'name': self.comp2.name,
                    'product_id': self.comp2.id,
                    'product_uom_qty': 1,
                    'product_uom_id': self.finished.uom_id.id,
                    'price_unit': 10,
                })
            ],
        })
        # recieving comp products will set their invetory valuation (creates SVLs)
        purchase_comps.button_confirm()
        purchase_comps.picking_ids.move_ids.picked = True
        purchase_comps.picking_ids.button_validate()

        purchase = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [Command.create({
                'name': self.finished.name,
                'product_id': self.finished.id,
                'product_uom_qty': 1,
                'product_uom_id': self.finished.uom_id.id,
                'price_unit': 100,
            })],
        })
        # validate subcontractor resupply
        purchase.button_confirm()
        resupply_picks = purchase._get_subcontracting_resupplies()
        resupply_picks.move_ids.picked = True
        resupply_picks.button_validate()
        # receive subcontracted product (MO will be done)
        receipt = purchase.picking_ids
        receipt.move_ids.picked = True
        receipt.button_validate()
        # create bill
        purchase.action_create_invoice()
        aml = self.env['account.move.line'].search([('purchase_line_id', '=', purchase.order_line.id)])
        # add 50 per unit ( 50 x 1 ) = 50 extra valuation
        aml.price_unit = 150
        aml.move_id.invoice_date = Date.today()
        aml.move_id.action_post()
        svl = aml.stock_valuation_layer_ids
        self.assertEqual(len(svl), 1)
        self.assertEqual(svl.value, 50)
        # check for the automated inventory valuation
        account_move_credit_line = svl.account_move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(account_move_credit_line.account_id.id, stock_in_acc_id)
        self.assertEqual(account_move_credit_line.credit, 50)
        # Total value of subcontracted product = 150 new price + components (10 + 10)
        self.assertEqual(self.finished.total_value, 170)
        self.assertEqual(self.finished.standard_price, 170)

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
                'product_uom_id': self.finished2.uom_id.id,
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
        return_picking = wizard._create_return()
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

        buy_route_id = self.ref('purchase_stock.route_warehouse0_buy')
        (self.finished | self.comp1 | self.comp2).route_ids = [(6, None, [buy_route_id])]
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
        # Resupply delay = 0 (received from MRP, where route type != "manufacture")
        # Vendor lead time = 15 (finished product supplier delay)
        # Manufacture lead time = 10 (BoM.produce_delay)
        # Max purchase component delay = max delay(comp1, comp2) + po_lead + days_to_purchase = 20
        self.assertEqual(bom_data['resupply_avail_delay'], 0 + 15 + 20 + 5 + 5,
            'Resupply avail delay = Resupply delay + Max(Vendor lead time, Manufacture lead time)'
            ' + Max purchase component delay + Purchase security lead time + Days to Purchase'
        )

        # Case 2: Vendor lead time < Manufacturing lead time + DTPMO on BOM
        self.bom.action_compute_bom_days()
        self.assertEqual(self.bom.days_to_prepare_mo, 10 + 5 + 5,
            "DTPMO = Purchase lead time(comp1) + Days to Purchase + Purchase security lead time")

        self.bom.days_to_prepare_mo = 10
        # Temp increase BoM.produce_delay, to check if it is now used in the final calculation
        self.bom.produce_delay = 30

        bom_data = self.env['report.mrp.report_bom_structure']._get_bom_data(self.bom, self.warehouse, self.finished)
        self.assertEqual(bom_data['lead_time'], 30 + 5 + 5 + 10,
            "Lead time = Manufacturing lead time + Days to Purchase + Purchase security lead time + DTPMO on BOM")
        # Resupply delay = 0 (received from MRP, where route type != "manufacture")
        # Vendor lead time = 15 (finished product supplier delay)
        # Manufacture lead time = 30 (BoM.produce_delay)
        # Max purchase component delay = max delay(comp1, comp2) + po_lead + days_to_purchase = 20
        self.assertEqual(bom_data['resupply_avail_delay'], 0 + 30 + 20 + 5 + 5,
            'Resupply avail delay = Resupply delay + Max(Vendor lead time, Manufacture lead time)'
            ' + Max purchase component delay + Purchase security lead time + Days to Purchase'
        )
        # Continue the test with the original produce_delay
        self.bom.produce_delay = 10

        # Update stock for components, calculate DTPMO should be 0
        self.env['stock.quant']._update_available_quantity(self.comp1, self.env.company.subcontracting_location_id, 100)
        self.env['stock.quant']._update_available_quantity(self.comp2, self.env.company.subcontracting_location_id, 100)
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
                'product_uom_id': self.finished.uom_id.id,
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
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        buy_route = self.env['stock.route'].search([('name', '=', 'Buy')])
        mto_route.active = True
        self.finished.route_ids = mto_route.ids + buy_route.ids
        self.env['product.supplierinfo'].create({
            'product_id': self.finished.id,
            'partner_id': self.vendor.id,
            'price': 12.0,
            'delay': 0
        })

        mo = self.env['mrp.production'].create({
            'product_id': self.finished2.id,
            'product_qty': 3.0,
            'move_raw_ids': [(0, 0, {
                'product_id': self.finished.id,
                'product_uom_qty': 3.0,
                'product_uom': self.finished.uom_id.id,
            })]
        })
        mo.action_confirm()
        po = self.env['purchase.order.line'].search([('product_id', '=', self.finished.id)]).order_id
        po.button_confirm()
        self.assertEqual(len(po.picking_ids), 1)
        picking = po.picking_ids
        picking.move_ids.quantity = 2.0
        # When we validate the picking manually, we create a backorder.
        Form.from_action(self.env, picking.button_validate()).save().process()
        self.assertEqual(len(po.picking_ids), 2)
        picking.backorder_ids.action_cancel()
        self.assertEqual(picking.backorder_ids.state, 'cancel')
        po.order_line.product_qty = 2.0
        self.assertEqual(po.order_line.product_qty, 2.0)

    def test_mrp_report_bom_structure_subcontracting_quantities(self):
        """Testing quantities and availablility states in subcontracted BoM report
        1. Create a BoM of a finished product with a single component
        2. Update the on hand quantity of BoM to 100
        3. Move 20 components to subcontracting location
        4. Check that the free/on-hand quantity of component is 100 (sum of warehouse stock and subcontracting location stock)
        5. Check that producible quantity of 'Product' is equal to only subcontractor location stock
        6. Check availability states when:
            6a. Search quantity <= subcontractor quantity: component is available
            6b. Subcontractor quantity <= search quantity <= total quantity: component is available
            6c. Total quantity < search quantity: component is unavailable
        """
        search_qty_less_than_or_equal_moved = 10
        moved_quantity_to_subcontractor = 20
        total_component_quantity = 100
        search_qty_more_than_total = 110

        resupply_route = self.env['stock.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        finished, component = self.env['product.product'].create([{
            'name': 'Finished Product',
            'is_storable': True,
            'seller_ids': [(0, 0, {'partner_id': self.subcontractor_partner1.id})]
        }, {
            'name': 'Component',
            'is_storable': True,
            'route_ids': [(4, resupply_route.id)],
        }])

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'subcontract',
            'subcontractor_ids': [(4, self.subcontractor_partner1.id)],
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1.0})],
        })

        self.env['stock.quant']._update_available_quantity(component, self.warehouse.lot_stock_id, total_component_quantity)
        # Check quantity was updated
        self.assertEqual(component.virtual_available, total_component_quantity)
        self.assertEqual(component.qty_available, total_component_quantity)

        quantity_before_move = self.env['stock.quant']._get_available_quantity(component, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.warehouse.subcontracting_resupply_type_id
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = component
            move.product_uom_qty = moved_quantity_to_subcontractor
        picking = picking_form.save()
        picking.action_confirm()
        picking.move_ids.quantity = moved_quantity_to_subcontractor
        picking.move_ids.picked = True
        picking.button_validate()
        quantity_after_move = self.env['stock.quant']._get_available_quantity(component, self.subcontractor_partner1.property_stock_subcontractor, allow_negative=True)
        self.assertEqual(quantity_after_move, quantity_before_move + moved_quantity_to_subcontractor)

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom.id, searchQty=search_qty_less_than_or_equal_moved, searchVariant=False)
        self.assertEqual(report_values['lines']['components'][0]['quantity_available'], moved_quantity_to_subcontractor)
        self.assertEqual(report_values['lines']['components'][0]['quantity_on_hand'], moved_quantity_to_subcontractor)
        self.assertEqual(report_values['lines']['quantity_available'], 0)
        self.assertEqual(report_values['lines']['quantity_on_hand'], 0)
        self.assertEqual(report_values['lines']['producible_qty'], moved_quantity_to_subcontractor)
        self.assertEqual(report_values['lines']['stock_avail_state'], 'unavailable')

        self.assertEqual(report_values['lines']['components'][0]['stock_avail_state'], 'available')

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom.id, searchQty=search_qty_less_than_or_equal_moved, searchVariant=False)
        self.assertEqual(report_values['lines']['components'][0]['stock_avail_state'], 'available')

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom.id, searchQty=search_qty_more_than_total, searchVariant=False)
        self.assertEqual(report_values['lines']['components'][0]['stock_avail_state'], 'unavailable')

    @freeze_time('2024-01-01')
    def test_bom_overview_availability_po_lead(self):
        # Create routes for components and the main product
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.finished.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'delay': 10
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp1.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'delay': 5
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp2.product_tmpl_id.id,
            'partner_id': self.subcontractor_partner1.id,
            'delay': 5
        })

        self.bom.produce_delay = 1
        self.bom.days_to_prepare_mo = 3
        # Security Lead Time for Purchase should always be added
        self.env.company.po_lead = 2

        # Add 4 units of each component to subcontractor's location
        subcontractor_location = self.env.company.subcontracting_location_id
        self.env['stock.quant']._update_available_quantity(self.comp1, subcontractor_location, 4)
        self.env['stock.quant']._update_available_quantity(self.comp2, subcontractor_location, 4)

        # Generate a report for 3 products: all products should be ready for production
        bom_data = self.env['report.mrp.report_bom_structure']._get_report_data(self.bom.id, 3)

        self.assertTrue(bom_data['lines']['components_available'])
        for component in bom_data['lines']['components']:
            self.assertEqual(component['quantity_on_hand'], 4)
            self.assertEqual(component['availability_state'], 'available')
        self.assertEqual(bom_data['lines']['earliest_capacity'], 3)
        # 01/11 + 2 days of Security Lead Time = 01/13
        self.assertEqual(bom_data['lines']['earliest_date'], '01/13/2024')
        self.assertTrue('leftover_capacity' not in bom_data['lines']['earliest_date'])
        self.assertTrue('leftover_date' not in bom_data['lines']['earliest_date'])

        # Generate a report for 5 products: only 4 products should be ready for production
        bom_data = self.env['report.mrp.report_bom_structure']._get_report_data(self.bom.id, 5)

        self.assertFalse(bom_data['lines']['components_available'])
        for component in bom_data['lines']['components']:
            self.assertEqual(component['quantity_on_hand'], 4)
            self.assertEqual(component['availability_state'], 'estimated')
        self.assertEqual(bom_data['lines']['earliest_capacity'], 4)
        # 01/11 + 2 days of Security Lead Time = 01/13
        self.assertEqual(bom_data['lines']['earliest_date'], '01/13/2024')
        self.assertEqual(bom_data['lines']['leftover_capacity'], 1)
        # 01/16 + 2 x 2 days (for components and for final product) = 01/20
        self.assertEqual(bom_data['lines']['leftover_date'], '01/20/2024')

    def test_location_after_dest_location_update_backorder_production(self):
        """
        Buy 2 subcontracted products.
        Receive 1 product after changing the destination location.
        Create a backorder.
        Receive the last one.
        Check the locations.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'group_ids': [Command.link(grp_multi_loc.id)]})
        subcontract_loc = self.env.company.subcontracting_location_id
        production_loc = self.finished.property_stock_production
        final_loc = self.env['stock.location'].create({
            'name': 'Final location',
            'location_id': self.env.ref('stock.warehouse0').lot_stock_id.id,
        })
        # buy 2 subcontracted products
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [Command.create({
                'name': self.finished.name,
                'product_id': self.finished.id,
                'product_qty': 2.0,
                'product_uom_id': self.finished.uom_id.id,
                'price_unit': 1.0,
            })],
        })
        po.button_confirm()

        receipt = po.picking_ids
        # receive 1 subcontracted product
        receipt.move_ids.quantity = 1
        receipt_form = Form(receipt)
        # change the destination location
        receipt_form.location_dest_id = final_loc
        receipt_form.save()
        # change the destination location on the move line too
        receipt.move_line_ids.location_dest_id = final_loc
        # create the backorder
        Form.from_action(self.env, receipt.button_validate()).save().process()
        backorder = receipt.backorder_ids
        # test the stock quantities after receiving 1 product
        stock_quants = self.env['stock.quant'].search([('product_id', '=', self.finished.id)])
        self.assertEqual(len(stock_quants), 3)
        self.assertEqual(stock_quants.filtered(lambda q: q.location_id == final_loc).quantity, 1.0)
        self.assertEqual(stock_quants.filtered(lambda q: q.location_id == subcontract_loc).quantity, 0.0)
        self.assertEqual(stock_quants.filtered(lambda q: q.location_id == production_loc).quantity, -1.0)
        # receive the last subcontracted product
        backorder.move_ids.quantity = 1
        backorder.button_validate()
        # test the final stock quantities
        stock_quants = self.env['stock.quant'].search([('product_id', '=', self.finished.id)])
        self.assertEqual(len(stock_quants), 3)
        self.assertEqual(stock_quants.filtered(lambda q: q.location_id == final_loc).quantity, 2.0)
        self.assertEqual(stock_quants.filtered(lambda q: q.location_id == subcontract_loc).quantity, 0.0)
        self.assertEqual(stock_quants.filtered(lambda q: q.location_id == production_loc).quantity, -2.0)

    def test_return_subcontracted_product_to_supplier_location(self):
        """
        Test that we can return subcontracted product to the supplier location.
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [Command.create({
                'name': self.finished.name,
                'product_id': self.finished.id,
                'product_qty': 2.0,
                'product_uom_id': self.finished.uom_id.id,
                'price_unit': 10.0,
            })],
        })

        po.button_confirm()
        self.assertEqual(len(po.picking_ids), 1)
        picking = po.picking_ids
        picking.button_validate()
        self.assertEqual(picking.state, 'done')
        # create a return to the vendor location
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        return_form = Form(self.env['stock.return.picking'].with_context(active_id=picking.id, active_model='stock.picking'))
        wizard = return_form.save()
        wizard.product_return_moves.quantity = 2.0
        return_picking = wizard._create_return()
        return_picking.location_dest_id = supplier_location
        return_picking.button_validate()
        self.assertEqual(return_picking.state, 'done')

    def test_global_visibility_days_affect_lead_time(self):
        """ Don't count global visibility days more than once, make sure a PO generated from
        replenishment/orderpoint has a sensible planned reception date.
        """
        wh = self.env.user._get_default_warehouse_id()
        self.finished2.seller_ids = [Command.create({
            'partner_id': self.subcontractor_partner1.id,
            'delay': 0,
        })]
        final_product = self.finished2
        orderpoint = self.env['stock.warehouse.orderpoint'].create({'product_id': final_product.id})
        out_picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': wh.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_ids': [Command.create({
                'product_id': final_product.id,
                'product_uom_qty': 2,
                'location_id': wh.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        out_picking.with_context(global_visibility_days=365).action_assign()
        r = orderpoint.action_stock_replenishment_info()
        repl_info = self.env[r['res_model']].browse(r['res_id'])
        lead_days_date = datetime.strptime(
            loads(repl_info.with_context(global_visibility_days=365).json_lead_days)['lead_days_date'],'%m/%d/%Y').date()
        self.assertEqual(lead_days_date, Date.today() + timedelta(days=365))

        orderpoint.action_replenish()
        purchase_order = self.env['purchase.order'].search([
            ('order_line', 'any', [
                ('product_id', '=', self.finished2.id),
            ]),
        ], limit=1)
        self.assertEqual(purchase_order.date_planned.date(), Date.today())

    @freeze_time('2000-05-01')
    def test_mrp_subcontract_modify_date(self):
        """ Ensure consistent results when modifying date fields of a weakly-linked reception and
        manufacturing order. Additionally, modifying `date_start` directly on an MO has a
        well-defined result.
        """
        self.bom_finished2.produce_delay = 35
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor_partner1.id,
            'order_line': [Command.create({
                'name': self.finished2.name,
                'product_id': self.finished2.id,
                'product_qty': 10,
                'product_uom_id': self.finished2.uom_id.id,
                'price_unit': 1,
            })],
        })
        po.button_confirm()
        mo = po.picking_ids.move_ids.move_orig_ids.production_id
        original_mo_start_date = mo.date_start
        with Form(po.picking_ids[0]) as receipt_form:
            receipt_form.scheduled_date = '2000-06-01'
        self.assertEqual(mo.date_start, datetime(year=2000, month=6, day=1) - timedelta(days=self.bom_finished2.produce_delay))
        with Form(po.picking_ids[0]) as receipt_form:
            receipt_form.scheduled_date = '2000-05-01'
        self.assertEqual(mo.date_start, original_mo_start_date)

        with Form(mo) as production_form:
            production_form.date_start = '2000-03-20'
        self.assertEqual(mo.date_start.date(), Date.to_date('2000-03-20'))
        with Form(mo) as production_form:
            production_form.date_start = original_mo_start_date
        self.assertEqual(mo.date_start, original_mo_start_date)
