from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools import float_compare
from .common import PurchaseTestCommon


@tagged('post_install', '-at_install')
class TestPurchaseOrderProcess(PurchaseTestCommon):

    def test_00_cancel_purchase_order_flow(self):
        """ Test cancel purchase order with group user."""

        # In order to test the cancel flow,start it from canceling confirmed purchase order.
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id,
            'state': 'draft',
        })
        po_edit_with_user = purchase_order.with_user(self.res_users_purchase_user)

        # Confirm the purchase order.
        po_edit_with_user.button_confirm()

        # Check the "Approved" status  after confirmed RFQ.
        self.assertEqual(po_edit_with_user.state, 'purchase', 'Purchase: PO state should be "Purchase')

        # First cancel receptions related to this order if order shipped.
        po_edit_with_user.picking_ids.action_cancel()

        # Able to cancel purchase order.
        po_edit_with_user.button_cancel()

        # Check that order is cancelled.
        self.assertEqual(po_edit_with_user.state, 'cancel', 'Purchase: PO state should be "Cancel')

    def test_02_vendor_delay_report_partially_cancelled_purchase_order(self):
        """ Test vendor delay reports for partially cancelled purchase order"""
        partner = self.partner_1
        purchase_order = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_1.id,
                    'product_qty': 2.0,
                    'product_uom_id': self.product_1.uom_id.id,
                }),
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 3.0,
                    'product_uom_id': self.product_2.uom_id.id,
                })],
        })
        purchase_order.button_confirm()
        purchase_order.picking_ids.move_ids.flush_recordset()
        delay_reports = self.env['vendor.delay.report']._read_group([('partner_id', '=', partner.id)], ['product_id'], ['on_time_rate:sum'])
        self.assertEqual([rec[1] for rec in delay_reports], [0.0, 0.0])
        # cancel the first part of the PO
        purchase_order.order_line.filtered(lambda l: l.product_id == self.product_1).product_qty = 0
        self.assertEqual(partner.purchase_order_count, 1)
        self.assertTrue(float_compare(partner.on_time_rate, 0.0, precision_rounding=0.01) <= 0, "negative number indicates no data")
        self.assertEqual(purchase_order.picking_ids.move_ids.filtered(lambda l: l.product_id == self.product_1).state, 'cancel')
        purchase_order.picking_ids.move_ids.filtered(lambda l: l.product_id == self.product_2).quantity = 3.0
        purchase_order.picking_ids.button_validate()
        self.assertEqual(purchase_order.picking_ids.move_ids.filtered(lambda l: l.product_id == self.product_2).state, 'done')
        self.assertEqual(partner.purchase_line_ids.mapped('qty_received'), [0.0, 3.0])
        partner.invalidate_recordset(fnames=['on_time_rate'])
        self.assertEqual(partner.on_time_rate, 100.0)
        purchase_order.picking_ids.move_ids.flush_recordset()
        delay_reports = self.env['vendor.delay.report']._read_group([('partner_id', '=', partner.id)], ['product_id'], ['on_time_rate:sum'])
        self.assertEqual([rec[1] for rec in delay_reports], [100.0])
