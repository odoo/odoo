# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import SkipTest

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account_payment.tests.common import AccountPaymentCommon


@tagged("post_install", "-at_install")
class TestInvoicePaymentStatusMatrix(AccountPaymentCommon):
    """The invoice rows of the payment status matrix. The portal list badge and the invoice page
    badge both show `_get_payment_status()`, so the method stands for both call sites."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.env["ir.module.module"]._get("payment_demo").state != "installed":
            msg = "The payment status matrix needs `payment_demo`"
            raise SkipTest(msg)

        cls.demo_provider = cls._prepare_provider(code="demo")
        cls.wire_provider = (
            cls
            .env["payment.provider"]
            .sudo()
            .search([("code", "=", "custom"), ("custom_mode", "=", "wire_transfer")], limit=1)
        )

    def _pay(self, invoice, amount, state, provider=None):
        provider = provider or self.demo_provider
        return self._create_transaction(
            "direct",
            provider_id=provider.id,
            payment_method_id=provider.with_context(active_test=False).payment_method_ids[:1].id,
            invoice_ids=[Command.set(invoice.ids)],
            partner_id=invoice.partner_id.id,
            currency_id=invoice.currency_id.id,
            amount=amount,
            state=state,
            reference=f"{invoice.name}-{len(invoice.transaction_ids)}",
        )

    def _build_scenario(self, scenario):
        invoice = self._create_invoice(post=True)
        total = invoice.amount_total
        half = invoice.currency_id.round(total / 2)
        if scenario == "split_paid_offline_and_authorized":
            self._register_payment(invoice, amount=half)
            self._pay(invoice, total - half, "authorized")
        elif scenario == "partial_authorized":
            self._pay(invoice, half, "authorized")
        elif scenario == "failed_retry_after_success":
            self._register_payment(invoice)
            self._pay(invoice, total, "error")
        elif scenario == "demo_pending":
            self._pay(invoice, total, "pending")
        elif scenario == "wire_transfer_pending":
            self._pay(invoice, total, "pending", provider=self.wire_provider)
        elif scenario == "wire_transfer_pending_paid_offline":
            self._pay(invoice, total, "pending", provider=self.wire_provider)
            self._register_payment(invoice)
        elif scenario == "demo_pending_after_partial_offline_payment":
            self._register_payment(invoice, amount=half)
            self._pay(invoice, total - half, "pending")
        elif scenario == "refund":
            invoice._reverse_moves(cancel=True)
        elif scenario == "cancelled":
            self._pay(invoice, total, "pending")
            invoice.button_cancel()
        return invoice

    def test_invoice_payment_status_considers_accounting_then_transactions(self):
        expected_by_scenario = {
            # Unlike the order's status, a settled part does not hide an authorized one. Same
            # result as master; the vocabulary's resolution order would say `partial`.
            "split_paid_offline_and_authorized": "authorized",
            "partial_authorized": "authorized",
            "failed_retry_after_success": "paid",
            "demo_pending": "pending",
            # Custom providers only promise a payment, so they don't make the invoice pending
            "wire_transfer_pending": "not_paid",
            "wire_transfer_pending_paid_offline": "paid",
            "demo_pending_after_partial_offline_payment": "pending",
            "refund": "reversed",
            "cancelled": "pending",  # The status ignores the invoice's own state
        }
        for scenario, expected in expected_by_scenario.items():
            with self.subTest(scenario=scenario):
                invoice = self._build_scenario(scenario)
                self.assertEqual(invoice._get_payment_status(), expected)
