# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestWhtClearing(AccountTestInvoicingCommon):
    """A WHT bearing expense payment must also clear the source payable."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wht_partner = cls.env["res.partner"].create({"name": "WHT Vendor"})
        cls.wht_payable_account = cls.env["account.account"].create({
            "name": "WHT Payable Test",
            "code": "219901",
            "account_type": "liability_current",
            "reconcile": True,
        })

    def _create_source_bill(self, amount=10000.0):
        """Post a tax-free vendor bill so the payable is exactly ``amount``."""
        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.wht_partner.id,
            "invoice_date": "2016-01-01",
            "date": "2016-01-01",
            "journal_id": self.company_data["default_journal_purchase"].id,
            "invoice_line_ids": [(0, 0, {
                "name": "WHT Service",
                "quantity": 1.0,
                "price_unit": amount,
                "account_id": self.company_data["default_account_expense"].id,
                "tax_ids": [(5, 0, 0)],
            })],
        })
        bill.action_post()
        return bill

    def _create_payment(self, amount=10000.0):
        return self.env["account.payment"].create({
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.wht_partner.id,
            "amount": amount,
            "journal_id": self.company_data["default_journal_bank"].id,
            "date": "2016-01-01",
            "od19_is_expense_payment": True,
            "od19_wht_type": "3",
            "od19_wht_base_amount": amount,
            "od19_wht_expense_account_id":
                self.company_data["default_account_expense"].id,
            "od19_wht_payable_account_id": self.wht_payable_account.id,
        })

    def _payable_lines(self):
        payable = self.wht_partner.with_company(
            self.env.company).property_account_payable_id
        return self.env["account.move.line"].search([
            ("account_id", "=", payable.id),
            ("partner_id", "=", self.wht_partner.id),
        ])

    def test_wht_move_created_and_posted(self):
        payment = self._create_payment()
        payment.action_post()

        self.assertAlmostEqual(payment.od19_wht_amount, 300.0)
        wht_move = payment.od19_wht_move_id
        self.assertTrue(wht_move)
        self.assertEqual(wht_move.state, "posted")
        wht_credit = wht_move.line_ids.filtered_domain([
            ("account_id", "=", self.wht_payable_account.id),
        ])
        self.assertAlmostEqual(sum(wht_credit.mapped("credit")), 300.0)

    def test_wht_payment_clears_source_payable(self):
        self._create_source_bill(10000.0)
        payment = self._create_payment(10000.0)
        payment.action_post()

        lines = self._payable_lines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(lines.mapped("reconciled")))
        self.assertAlmostEqual(sum(lines.mapped("amount_residual")), 0.0)

    def test_payment_without_wht_does_not_create_move(self):
        payment = self.env["account.payment"].create({
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.wht_partner.id,
            "amount": 1000.0,
            "journal_id": self.company_data["default_journal_bank"].id,
            "date": "2016-01-01",
            "od19_is_expense_payment": True,
        })
        payment.action_post()
        self.assertFalse(payment.od19_wht_move_id)
