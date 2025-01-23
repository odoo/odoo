# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form, new_test_user
from odoo import fields


@tagged('-at_install', 'post_install')
class TestPurchaseStockDashboard(AccountTestInvoicingCommon):

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

    def test_purchase_stock_dashboard(self):
        '''
        Test purchase stock dashboard values with multiple users.
        '''

        # Create 10 Request for Quotations with lines.
        rfqs = self.env['purchase.order'].create([{
            'partner_id': self.partner_a.id,
            'user_id': self.user_a.id if i < 6 else self.user_b.id,
            'company_id': self.user_a.company_id.id,
            'currency_id': self.user_a.company_id.currency_id.id,
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

        self.env.company.days_to_purchase = 7

        # Confirm RFQs and set planned dates
        for idx, rfq in enumerate(rfqs):
            rfq.button_confirm()
            date_offset = timedelta(days=idx + 1)
            rfq.write({'date_planned': fields.Datetime.now() - date_offset if idx % 2 == 0 else fields.Datetime.now() + date_offset})
            # Send a reminder mail to order
            if idx % 4 == 0:
                rfq.confirm_reminder_mail()
            # Validate picking for every third order
            if idx % 3 == 0:
                rfq.picking_ids.button_validate()

        # Retrieve dashboard as User A to check all values.
        dashboard_result = rfqs.with_user(self.user_a).retrieve_dashboard()

        self.assertEqual(dashboard_result['all_late_orders'], 3)
        self.assertEqual(dashboard_result['my_late_orders'], 2)
        self.assertEqual(dashboard_result['default_days_to_purchase'], 7)
        self.assertEqual(dashboard_result['all_on_time_delivery'], 20.00)
        self.assertEqual(dashboard_result['my_on_time_delivery'], 16.67)
