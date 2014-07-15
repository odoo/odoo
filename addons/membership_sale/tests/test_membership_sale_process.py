# -*- coding: utf-8 -*-
import datetime
from openerp.addons.membership_sale.tests.common import TestMembershipSale

class TestSalemembership(TestMembershipSale):

    def test_membership_sale(self):

        order_id1 = self.sale_order.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_id})]
        })
        order_id1.action_button_confirm()
        membership_line_ids = self.membership_line.search(
            [('sale_order_id', '=', order_id1.id)])
        self.assertTrue(
            membership_line_ids, 'Membership Line: Creation of Membership Line failed.')
        self.assertEqual(
            membership_line_ids.state, 'waiting', 'Membership is not in Waiting state')

        res = order_id1.manual_invoice()
        invoice_id = res.get('res_id')
        invoice = self.invoice_line.browse(invoice_id)
        invoice.signal_workflow('invoice_open')

        membership_line_ids = self.membership_line.search(
            [('sale_order_id', '=', order_id1.id)])
        assert membership_line_ids, "Membership Line: Creation of Membership Line failed."
        self.assertEqual(
            membership_line_ids.state, 'invoiced', 'invoice is not created ,membership is not in invoiced state')
        self.assertTrue(
            membership_line_ids.account_invoice_line, 'Invoice is not confirmed.')
