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
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

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

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_purchase_dashboard(self):
        '''
        Test purchase dashboard values with multiple users.
        '''

        # Create 3 Request for Quotations with lines.
        rfqs = self.env['purchase.order'].create([{
            'partner_id': self.partner_a.id,
            'company_id': self.user_a.company_id.id,
            'currency_id': self.user_a.company_id.currency_id.id,
            'date_order': fields.Date.today(),
        } for i in range(3)])
        for rfq, qty in zip(rfqs, [1, 2, 3]):
            rfq_form = Form(rfq)
            with rfq_form.order_line.new() as line_1:
                line_1.product_id = self.product_100
                line_1.product_qty = qty
            with rfq_form.order_line.new() as line_2:
                line_2.product_id = self.product_250
                line_2.product_qty = qty
            rfq_form.save()

        # Create 1 late RFQ without line.
        self.env['purchase.order'].create([{
            'partner_id': self.partner_a.id,
            'company_id': self.user_a.company_id.id,
            'currency_id': self.user_a.company_id.currency_id.id,
            'date_order': fields.Date.today() - timedelta(days=7)
        }])

        # Create 1 draft RFQ for user A.
        self.env['purchase.order'].with_user(self.user_a).create([{
            'partner_id': self.partner_a.id,
            'company_id': self.user_a.company_id.id,
            'currency_id': self.user_a.company_id.currency_id.id,
            'date_order': fields.Date().today() + timedelta(days=7)
        }])

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

        # Confirm Orders with lines.
        rfqs.button_confirm()
        # Retrieve dashboard as User A to check 'my_{to_send, waiting, late}' values.
        dashboard_result = rfqs.with_user(self.user_a).retrieve_dashboard()

        # Check dashboard values
        currency_id = self.env.company.currency_id
        zero_value_keys = ['all_waiting', 'my_waiting', 'my_late']
        self.assertListEqual([dashboard_result[key] for key in zero_value_keys], [0]*len(zero_value_keys))
        self.assertEqual(dashboard_result['all_to_send'], 2)
        self.assertEqual(dashboard_result['my_to_send'], 1)
        self.assertEqual(dashboard_result['all_late'], 1)
        self.assertEqual(dashboard_result['all_avg_order_value'], format_amount(self.env, self.tax_purchase_a.compute_all(700.0)['total_included'], currency_id))
        self.assertEqual(dashboard_result['all_avg_days_to_purchase'], 0)
        self.assertEqual(dashboard_result['all_total_last_7_days'], format_amount(self.env, self.tax_purchase_a.compute_all(2100.0)['total_included'], currency_id))
        self.assertEqual(dashboard_result['all_sent_rfqs'], 2)
