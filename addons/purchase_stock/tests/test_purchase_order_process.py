from odoo import Command, fields
from odoo.tests import Form, tagged, users
from odoo.tools import float_compare

from .common import PurchaseTestCommon


@tagged('post_install', '-at_install')
class TestPurchaseOrderProcess(PurchaseTestCommon):

    @users('purchase_user')
    def test_00_cancel_purchase_order_flow(self):
        """ Test cancel purchase order with group user."""

        # In order to test the cancel flow,start it from canceling confirmed purchase order.
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'state': 'draft',
        })

        # Confirm the purchase order.
        purchase_order.button_confirm()

        # Check the "Approved" status  after confirmed RFQ.
        self.assertEqual(purchase_order.state, 'purchase', 'Purchase: PO state should be "Purchase')

        # First cancel receptions related to this order if order shipped.
        purchase_order.picking_ids.action_cancel()

        # Able to cancel purchase order.
        purchase_order.button_cancel()

        # Check that order is cancelled.
        self.assertEqual(purchase_order.state, 'cancel', 'Purchase: PO state should be "Cancel')

    def test_02_vendor_delay_report_partially_cancelled_purchase_order(self):
        """ Test vendor delay reports for partially cancelled purchase order"""
        self.product_2 = self.product.copy()
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_qty': 2.0,
                    'product_uom_id': self.uom.id,
                }),
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 3.0,
                    'product_uom_id': self.uom.id,
                })],
        })
        purchase_order.button_confirm()
        purchase_order.order_line.flush_recordset()
        purchase_order.picking_ids.move_ids.flush_recordset()
        delay_reports = self.env['vendor.delay.report']._read_group([('partner_id', '=', self.vendor.id)], ['product_id'], ['on_time_rate:sum'])
        self.assertEqual([rec[1] for rec in delay_reports], [0.0, 0.0])
        # cancel the first part of the PO
        purchase_order.order_line.filtered(lambda l: l.product_id == self.product).product_qty = 0
        self.assertEqual(self.vendor.purchase_order_count, 1)
        self.assertTrue(float_compare(self.vendor.on_time_rate, 0.0, precision_rounding=0.01) <= 0, "negative number indicates no data")
        self.assertEqual(purchase_order.picking_ids.move_ids.filtered(lambda l: l.product_id == self.product).state, 'cancel')
        purchase_order.picking_ids.move_ids.filtered(lambda l: l.product_id == self.product_2).quantity = 3.0
        purchase_order.picking_ids.button_validate()
        self.assertEqual(purchase_order.picking_ids.move_ids.filtered(lambda l: l.product_id == self.product_2).state, 'done')
        self.assertEqual(self.vendor.purchase_line_ids.mapped('qty_received'), [0.0, 3.0])
        self.vendor.invalidate_recordset(fnames=['on_time_rate'])
        self.assertEqual(self.vendor.on_time_rate, 100.0)
        purchase_order.picking_ids.move_ids.flush_recordset()
        delay_reports = self.env['vendor.delay.report']._read_group([('partner_id', '=', self.vendor.id)], ['product_id'], ['on_time_rate:sum'])
        self.assertEqual([rec[1] for rec in delay_reports], [100.0])

    def test_cancel_redraft_fulfilled(self):
        """Test whether cancelling a fulfilled purchase order will leave
           the done picking intact and redrafting it will not create a new
           picking."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_qty': 2.0,
                }),
            ],
        })
        po.button_confirm()

        picking = po.picking_ids[0]
        picking.button_validate()

        po.button_cancel()
        self.assertEqual(po.state, 'cancel')
        self.assertEqual(picking.state, 'done', "Done pickings should not change state.")

        po.button_draft()
        self.assertEqual(po.state, 'draft', "The PO should gracefully return to draft state.")
        self.assertEqual(picking.state, 'done', "Done pickings should not change state.")

        po.button_confirm()
        self.assertEqual(po.state, 'purchase')
        self.assertEqual(len(po.picking_ids), 1, "No new pickings should be created for a fulfilled PO.")

    def test_cancel_redraft_backordered(self):
        """Test whether cancelling a partially fulfilled purchase order and
           redrafting it will create a backorder with the remaining undelivered
           quantity, and that cancelling the order will propagate to the
           unfulfilled backorder as well. Redrafting the PO should create a
           new picking to compensate for the quantity left undelivered."""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_qty': 5.0,
                }),
            ],
        })
        po.button_confirm()

        # Receive less than the expected amount.
        picking = po.picking_ids[0]
        move = picking.move_ids[0]
        move.quantity = 3.0
        action = picking.button_validate()

        # Create a backorder for the rest.
        Form(self.env['stock.backorder.confirmation'].with_context(action['context'])).save().process()
        remainder_qty = po.order_line.product_qty - move.quantity
        backorder = picking.backorder_ids[0]
        self.assertEqual(po.order_line.qty_received, move.quantity, "Only the quantity set in the picking should be received.")
        self.assertEqual(backorder.move_ids.quantity, remainder_qty, "The backorder should contain the unreceived quantity.")

        po.button_cancel()
        self.assertEqual(po.state, 'cancel')
        self.assertEqual(picking.state, 'done', "Done pickings should not change state.")
        self.assertEqual(backorder.state, 'cancel', "The backorder should be cancelled with the PO, as it was not validated.")

        po.button_draft()
        self.assertEqual(po.state, 'draft', "The PO should gracefully return to draft state.")

        po.button_confirm()
        self.assertEqual(po.state, 'purchase')
        self.assertEqual(len(po.picking_ids), 3, "A new picking should be created to compensate for the cancelled backorder.")

        new_picking = po.picking_ids - picking - backorder
        self.assertEqual(new_picking.move_ids.quantity, remainder_qty, "The newly created picking should contain the amount left undelivered.")

        new_picking.move_ids.picked = True
        new_picking.button_validate()
        self.assertEqual(po.order_line.qty_received, po.order_line.product_qty, "We should have received the entire quantity specified in the PO.")
