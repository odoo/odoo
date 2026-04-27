# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.approvals_purchase_stock.tests.common import TestApprovalsCommon

class TestApprovalsPurchaseStock(TestApprovalsCommon):

    def test_warehouse_01(self):
        """ Check when a Purchase Request Approval with two product lines with
        different warehouse will create two different purchase orders. """
        request_form = self.create_request_form(approver=self.user_approver)
        # Create a purchase product line.
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_computer
            line.quantity = 2
            line.warehouse_id = self.warehouse_1
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_computer
            line.quantity = 4
            line.warehouse_id = self.warehouse_2
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(self.user_approver).action_approve()
        request_purchase.action_create_purchase_orders()

        self.assertEqual(request_purchase.purchase_order_count, 2)

        po_1 = request_purchase.product_line_ids[0].purchase_order_line_id.order_id
        po_2 = request_purchase.product_line_ids[1].purchase_order_line_id.order_id
        self.assertEqual(po_1.picking_type_id.id, self.wh_picking_type_1.id)
        self.assertEqual(po_2.picking_type_id.id, self.wh_picking_type_2.id)

        # Confirm POs via smart button and check pickings are created
        button_context = request_purchase.action_open_purchase_orders()['context']
        po_1.with_context(button_context).button_confirm()
        po_2.with_context(button_context).button_confirm()
