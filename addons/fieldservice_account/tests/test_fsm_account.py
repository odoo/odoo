# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase


class FSMAccountCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Wizard = self.env["fsm.wizard"]
        self.WorkOrder = self.env["fsm.order"]
        self.AccountInvoice = self.env["account.move"]
        self.AccountInvoiceLine = self.env["account.move.line"]
        # create a Res Partner
        self.test_partner = self.env["res.partner"].create(
            {"name": "Test Partner", "phone": "123", "email": "tp@email.com"}
        )
        # create a Res Partner to be converted to FSM Location/Person
        self.test_loc_partner = self.env["res.partner"].create(
            {"name": "Test Loc Partner", "phone": "ABC", "email": "tlp@email.com"}
        )
        self.test_loc_partner2 = self.env["res.partner"].create(
            {"name": "Test Loc Partner 2", "phone": "123", "email": "tlp@example.com"}
        )
        # create expected FSM Location to compare to converted FSM Location
        self.test_location = self.env["fsm.location"].create(
            {
                "name": "Test Location",
                "phone": "123",
                "email": "tp@email.com",
                "partner_id": self.test_loc_partner.id,
                "owner_id": self.test_loc_partner.id,
            }
        )
        self.test_order = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "date_start": datetime.today(),
                "date_end": datetime.today() + timedelta(hours=2),
                "request_early": datetime.today(),
            }
        )
        self.test_order2 = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "date_start": datetime.today(),
                "date_end": datetime.today() + timedelta(hours=2),
                "request_early": datetime.today(),
            }
        )
        company = self.env.user.company_id

        self.default_account_revenue = self.env["account.account"].search(
            [
                ("company_ids", "in", company.id),
                ("account_type", "=", "income"),
                (
                    "id",
                    "!=",
                    company.account_journal_early_pay_discount_gain_account_id.id,
                ),
            ],
            limit=1,
        )

        self.test_invoice = self.env["account.move"].create(
            {
                "partner_id": self.test_partner.id,
                "move_type": "out_invoice",
                "invoice_date": datetime.today().date(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test",
                            "quantity": 1.00,
                            "price_unit": 100.00,
                        },
                    )
                ],
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "line_debit",
                            "account_id": self.default_account_revenue.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "line_credit",
                            "account_id": self.default_account_revenue.id,
                        },
                    ),
                ],
            }
        )
        self.test_invoice2 = self.env["account.move"].create(
            {
                "partner_id": self.test_partner.id,
                "move_type": "out_invoice",
                "invoice_date": datetime.today().date(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test1",
                            "quantity": 1.00,
                            "price_unit": 100.00,
                        },
                    )
                ],
            }
        )

    def test_fsm_account(self):
        # Set invoice lines on Test Order 1
        self.test_order.invoice_lines = [(6, 0, self.test_invoice.line_ids.ids)]
        # Verify invoice is correctly linked to FSM Order
        self.test_order._compute_get_invoiced()
        self.assertEqual(self.test_order.invoice_count, 1)
        self.assertEqual(self.test_invoice.id, self.test_order.invoice_ids.ids[0])
        # Verify FSM Order is correctly linked to invoice
        self.test_invoice._compute_fsm_order_ids()
        self.assertEqual(self.test_invoice.fsm_order_count, 1)
        self.assertEqual(self.test_order.id, self.test_invoice.fsm_order_ids.ids[0])
        # Verify action result to view one invoice from order
        action_view_inv = self.test_order.action_view_invoices()
        self.assertEqual(action_view_inv.get("res_id"), self.test_invoice.id)
        # Verify action result to view one FSM Order from invoice
        action_view_order = self.test_invoice.action_view_fsm_orders()
        self.assertEqual(action_view_order.get("res_id"), self.test_order.id)
        # Set invoice lines on Test Order 2
        self.test_order2.invoice_lines = [(6, 0, self.test_invoice.line_ids.ids)]
        # Verify 2 FSM Orders are now linked to the invoice
        self.test_invoice._compute_fsm_order_ids()
        self.assertEqual(self.test_invoice.fsm_order_count, 2)
        # Verify action result to view two orders from invoice
        view_order_action = self.test_invoice.action_view_fsm_orders()
        self.assertTrue(view_order_action.get("domain"))
        # Add a second set of invoice lines to Test Order 1
        lines = self.test_invoice.line_ids.ids + self.test_invoice2.line_ids.ids
        self.test_order.invoice_lines = [(6, 0, lines)]
        # Verify 2 invoices are linked to the FSM Order
        self.test_order._compute_get_invoiced()
        self.assertEqual(self.test_order.invoice_count, 2)
        # Verify action result to view two invoices from order
        action_view_inv = self.test_order.action_view_invoices()
        self.assertTrue(action_view_inv.get("domain"))
