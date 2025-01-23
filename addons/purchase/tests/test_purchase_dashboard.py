# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCase
from odoo.tests import tagged, Form, new_test_user
from odoo.tools import mute_logger, format_amount
from odoo import fields

@tagged('-at_install', 'post_install')
class TestPurchaseDashboard(AccountTestInvoicingCommon, MailCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create two new users
        cls.user_a = new_test_user(cls.env, login='purchaseusera', groups='purchase.group_purchase_user')
        cls.user_b = new_test_user(cls.env, login='purchaseuserb', groups='purchase.group_purchase_user')

        # Create two products.
        product_data = {
            'name': 'SuperProduct',
            'type': 'consu',
        }
        cls.product_100 = cls.env['product.product'].create({**product_data, 'standard_price': 100})
        cls.product_250 = cls.env['product.product'].create({**product_data, 'standard_price': 250})

    @classmethod
    def default_env_context(cls):
        # OVERRIDE
        return {}

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_purchase_dashboard(self):
        '''
        Test purchase dashboard values with multiple users.
        '''

        # Create 10 Request for Quotations with lines.
        rfqs = self.env['purchase.order'].create([{
            'partner_id': self.partner_a.id,
            'user_id': self.user_a.id if i < 6 else self.user_b.id,
            'company_id': self.user_a.company_id.id,
            'currency_id': self.user_a.company_id.currency_id.id,
            'date_order': fields.Date.today() - timedelta(days=i),
            'priority': '1' if i % 2 == 0 else '0',
        } for i in range(10)])
        for rfq, qty in zip(rfqs, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]):
            rfq_form = Form(rfq)
            with rfq_form.order_line.new() as line_1:
                line_1.product_id = self.product_100
                line_1.product_qty = qty
            with rfq_form.order_line.new() as line_2:
                line_2.product_id = self.product_250
                line_2.product_qty = qty
            rfq_form.save()

        self.flush_tracking()
        with self.mock_mail_gateway():
            rfqs[0].with_user(self.user_a).write({'state': 'sent'})
            self.flush_tracking()
        # Sanity checks for rfq state.
        self.assertEqual(rfqs[0].state, 'sent')
        with self.mock_mail_gateway():
            rfqs[1].with_user(self.user_b).write({'state': 'sent'})
            self.flush_tracking()
        self.assertEqual(rfqs[1].state, 'sent')

        # Confirm the purchase orders.
        for idx, rfq in enumerate(rfqs):
            if idx in (0, 1):
                continue
            if idx % 3 == 0:
                rfq.button_confirm()
                date_offset = timedelta(days=idx + 1)
                rfq.write({'date_approve': fields.Datetime.now() - date_offset if idx % 2 == 0 else fields.Datetime.now() + date_offset})

        # Send a reminder mail for the 4th order in the list.
        rfqs[3].confirm_reminder_mail()

        # Retrieve dashboard as User A to check all values.
        dashboard_result = rfqs.with_user(self.user_a).retrieve_dashboard()

        # Check dashboard values
        self.assertEqual(dashboard_result['all_draft_rfqs'], 5)
        self.assertEqual(dashboard_result['my_draft_rfqs'], 3)
        self.assertEqual(dashboard_result['all_priority_draft_rfqs'], 3)
        self.assertEqual(dashboard_result['my_priority_draft_rfqs'], 2)
        self.assertEqual(dashboard_result['all_sent_rfqs'], 2)
        self.assertEqual(dashboard_result['my_sent_rfqs'], 2)
        self.assertEqual(dashboard_result['all_late_rfqs'], 7)
        self.assertEqual(dashboard_result['my_late_rfqs'], 5)
        self.assertEqual(dashboard_result['all_not_acknowledged_orders'], 3)
        self.assertEqual(dashboard_result['my_not_acknowledged_orders'], 1)
        self.assertEqual(dashboard_result['all_avg_days_to_purchase'], 2.33)
        self.assertEqual(dashboard_result['my_avg_days_to_purchase'], 4)
        self.assertEqual(dashboard_result['default_days_to_purchase'], 0)
