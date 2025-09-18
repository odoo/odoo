# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import MailCase
from odoo.tests import tagged, Form, new_test_user
from odoo.tools import mute_logger, format_amount
from odoo import fields


@tagged("-at_install", "post_install")
class TestPurchaseDashboard(AccountTestInvoicingCommon, MailCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create two new users
        # user_a needs group_purchase_user_all to see all POs for global dashboard counts
        cls.user_a = new_test_user(
            cls.env,
            login="purchaseusera",
            groups="purchase.group_purchase_user,purchase.group_purchase_user_all",
        )
        cls.user_b = new_test_user(
            cls.env, login="purchaseuserb", groups="purchase.group_purchase_user"
        )

        # Create two products.
        product_data = {
            "name": "SuperProduct",
            "type": "consu",
        }
        cls.product_100 = cls.env["product.product"].create(
            {**product_data, "standard_price": 100}
        )
        cls.product_250 = cls.env["product.product"].create(
            {**product_data, "standard_price": 250}
        )

    @classmethod
    def default_env_context(cls):
        # OVERRIDE
        return {}

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_purchase_dashboard(self):
        """Test purchase dashboard values with multiple users."""

        # Create 3 Request for Quotations with lines.
        # Set user_id to allow access via personal purchase order rule
        rfqs = self.env["purchase.order"].create(
            [
                {
                    "partner_id": self.partner_a.id,
                    "company_id": self.user_a.company_id.id,
                    "currency_id": self.user_a.company_id.currency_id.id,
                    "date_order": fields.Date.today(),
                    "user_id": self.user_a.id if i == 0 else self.user_b.id,
                }
                for i in range(3)
            ]
        )
        for rfq, qty in zip(rfqs, [1, 2, 3]):
            rfq_form = Form(rfq)
            with rfq_form.line_ids.new() as line_1:
                line_1.product_id = self.product_100
                line_1.product_qty = qty
            with rfq_form.line_ids.new() as line_2:
                line_2.product_id = self.product_250
                line_2.product_qty = qty
            rfq_form.save()

        # Create 1 late RFQ without line (assigned to user_b so user_a sees 0 in 'my' late).
        self.env["purchase.order"].create(
            [
                {
                    "partner_id": self.partner_a.id,
                    "company_id": self.user_a.company_id.id,
                    "currency_id": self.user_a.company_id.currency_id.id,
                    "date_order": fields.Date.today() - timedelta(days=7),
                    "user_id": self.user_b.id,
                }
            ]
        )

        # Create 1 draft RFQ for user A.
        self.env["purchase.order"].with_user(self.user_a).create(
            [
                {
                    "partner_id": self.partner_a.id,
                    "company_id": self.user_a.company_id.id,
                    "currency_id": self.user_a.company_id.currency_id.id,
                    "priority": "1",
                    "date_order": fields.Date().today() + timedelta(days=7),
                }
            ]
        )

        self.flush_tracking()
        with self.mock_mail_gateway():
            rfqs[0].with_user(self.user_a).write({"sent": True})
            self.flush_tracking()
        # Sanity checks for rfq sent flag.
        self.assertTrue(rfqs[0].sent)
        with self.mock_mail_gateway():
            rfqs[1].with_user(self.user_b).write({"sent": True})
            self.flush_tracking()
        self.assertTrue(rfqs[1].sent)

        # Confirm Orders with lines.
        rfqs.action_confirm()
        # Retrieve dashboard as User A to check 'my_{to_send, waiting, late}' values.
        dashboard_result = rfqs.with_user(self.user_a).prepare_dashboard()

        # Check dashboard values
        currency_id = self.env.company.currency_id

        self.assertFalse(dashboard_result["global"]["sent"]["all"])
        self.assertFalse(dashboard_result["my"]["late"]["all"])
        self.assertEqual(dashboard_result["global"]["draft"]["all"], 2)
        self.assertEqual(dashboard_result["global"]["draft"]["priority"], 1)
        self.assertEqual(dashboard_result["my"]["draft"]["all"], 1)
        self.assertEqual(dashboard_result["global"]["late"]["all"], 1)
