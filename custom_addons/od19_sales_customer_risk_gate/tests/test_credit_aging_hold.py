from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestCreditAgingHold(CreditGateCommon):
    """Tests for the rolling credit limit and the automatic ageing hold."""

    def setUp(self):
        super().setUp()
        self.env.company.write(
            {
                "od19_credit_hold_enabled": True,
                "od19_credit_hold_max_overdue_days": 30,
                "od19_credit_hold_max_overdue_amount": 0.0,
            }
        )

    def _approve_credit(self, limit=10000.0):
        self.customer.od19_credit_review_note = "ok"
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.with_user(self.reviewer).action_od19_approve_credit()
        self.customer.sudo().od19_credit_limit_amount = limit

    def _make_overdue_invoice(self, days=45, amount=100.0):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.contact.id,
                "invoice_date": fields.Date.today() - timedelta(days=days),
                "invoice_date_due": fields.Date.today() - timedelta(days=days),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": 1,
                            "price_unit": amount,
                        },
                    )
                ],
            }
        )
        move.action_post()
        return move

    def test_no_overdue_no_hold(self):
        self._approve_credit()
        self.customer._compute_od19_credit_aging()
        self.assertEqual(self.customer.od19_credit_overdue_amount, 0.0)
        self.assertEqual(self.customer.od19_credit_oldest_overdue_days, 0)
        self.assertFalse(self.customer.od19_credit_on_hold)

    def test_hold_when_overdue_days_exceeded(self):
        self._approve_credit()
        self._make_overdue_invoice(days=45, amount=100.0)
        self.customer._compute_od19_credit_aging()
        self.assertEqual(self.customer.od19_credit_oldest_overdue_days, 45)
        self.assertGreaterEqual(self.customer.od19_credit_overdue_amount, 100.0)
        self.assertTrue(self.customer.od19_credit_on_hold)
        self.assertIn("45", self.customer.od19_credit_hold_reason)

    def test_hold_when_overdue_amount_exceeded(self):
        # Disable the day test and rely on the amount tolerance only.
        self.env.company.od19_credit_hold_max_overdue_days = 0
        self.env.company.od19_credit_hold_max_overdue_amount = 50.0
        self._approve_credit()
        self._make_overdue_invoice(days=5, amount=200.0)
        self.customer._compute_od19_credit_aging()
        self.assertTrue(self.customer.od19_credit_on_hold)

    def test_rolling_limit_reduces_by_overdue(self):
        self._approve_credit(limit=1000.0)
        self._make_overdue_invoice(days=45, amount=200.0)
        self.customer._compute_od19_credit_aging()
        self.assertEqual(self.customer.od19_credit_rolling_limit, 800.0)

    def test_available_uses_rolling_limit(self):
        self._approve_credit(limit=1000.0)
        self._make_overdue_invoice(days=45, amount=200.0)
        self.customer._compute_od19_credit_aging()
        self.customer._compute_od19_credit_used_amount()
        self.customer._compute_od19_credit_available()
        # rolling limit 800 - used 200 = 600
        self.assertEqual(self.customer.od19_credit_available, 600.0)

    def test_gate_blocks_credit_sale_when_on_hold(self):
        self._approve_credit()
        self._make_overdue_invoice(days=45, amount=100.0)
        self.customer._compute_od19_credit_aging()
        # Credit is still approved and the limit is high enough, so the block
        # is caused by the ageing hold and not by lack of credit.
        self.customer._compute_od19_credit_sale_allowed()
        self.assertTrue(self.customer.od19_credit_sale_allowed)
        with self.assertRaisesRegex(UserError, "credit_hold"):
            self.env["sale.order"].create(
                self._quotation_vals(self.contact, self.term_30)
            )

    def test_hold_not_applied_when_credit_not_approved(self):
        # Not approved -> the customer is already blocked for credit sales;
        # the ageing hold must stay off so it does not mask the real reason.
        self._make_overdue_invoice(days=90, amount=500.0)
        self.customer._compute_od19_credit_aging()
        self.assertFalse(self.customer.od19_credit_on_hold)

    def test_hold_disabled_by_partner_toggle(self):
        self._approve_credit()
        self.customer.sudo().od19_credit_aging_hold_enabled = False
        self._make_overdue_invoice(days=45, amount=100.0)
        self.customer._compute_od19_credit_aging()
        self.assertFalse(self.customer.od19_credit_on_hold)

    def test_cron_recheck_runs(self):
        self._approve_credit()
        self._make_overdue_invoice(days=45, amount=100.0)
        # The nightly scheduler must run without raising.
        self.env["res.partner"]._cron_od19_recheck_credit_aging()
