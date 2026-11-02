from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSalesRetention(TransactionCase):
    """Tests for the retention (เงินประกันผลงาน) workflow.

    Acceptance criteria (Wave 6.2 / WS-02):

    * a 1,000,000 installment withheld at 5% is invoiced for the **full**
      1,070,000 (VAT inclusive);
    * the 53,500 retention lands in the retention receivable account, leaving
      the reported output VAT (ภ.พ.30) untouched;
    * once released the retention can be closed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contractor = cls.env["res.partner"].create({"name": "Contractor RET"})
        cls.owner = cls.env["res.partner"].create(
            {
                "name": "Owner RET",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        cls.project = cls.env["project.project"].create(
            {"name": "Retention Project", "project_owner_id": cls.owner.id}
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Customer RET", "is_company": True}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Service RET",
                "type": "service",
                "list_price": 1000000.0,
            }
        )
        cls.vat = cls.env["account.tax"].create(
            {
                "name": "VAT 7% RET",
                "amount": 7.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        cls.retention_account = cls.env["account.account"].create(
            {
                "name": "Retention Receivable RET",
                "code": "123999",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.retention_journal = cls.env["account.journal"].create(
            {
                "name": "Retention Journal RET",
                "code": "RETJ",
                "type": "general",
            }
        )

    def _make_contract(self, limit=1000000.0, rate=5.0, days=365):
        return self.env["od19.sales.contract"].create(
            {
                "name": "MC-RET-0001",
                "partner_id": self.contractor.id,
                "od19_project_id": self.project.id,
                "limit_amount": limit,
                "over_limit_policy": "warn",
                "od19_default_retention_rate": rate,
                "od19_default_retention_days": days,
                "od19_retention_account_id": self.retention_account.id,
                "od19_retention_journal_id": self.retention_journal.id,
            }
        )

    def _make_invoice(self, amount=1000000.0):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": fields.Date.context_today(self),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "quantity": 1.0,
                            "price_unit": amount,
                            "tax_ids": [(6, 0, [self.vat.id])],
                        },
                    )
                ],
            }
        )

    def _link_billing_line(self, contract, invoice, percent=100.0):
        return self.env["od19.contract.billing.line"].create(
            {
                "name": "Installment 1",
                "contract_id": contract.id,
                "sequence": 1,
                "line_type": "percent",
                "percent": percent,
                "invoice_id": invoice.id,
            }
        )

    def test_hold_keeps_full_invoice_and_separates_retention(self):
        contract = self._make_contract()
        invoice = self._make_invoice(amount=1000000.0)
        self.assertAlmostEqual(invoice.amount_untaxed, 1000000.0, 2)
        self.assertAlmostEqual(invoice.amount_total, 1070000.0, 2)
        line = self._link_billing_line(contract, invoice)
        self.assertAlmostEqual(line.od19_retention_rate, 5.0, 2)

        invoice.action_post()

        # Invoice stays at the full amount -> output VAT unchanged.
        self.assertEqual(invoice.state, "posted")
        self.assertAlmostEqual(invoice.amount_untaxed, 1000000.0, 2)
        self.assertAlmostEqual(invoice.amount_total, 1070000.0, 2)
        self.assertAlmostEqual(invoice.amount_total - invoice.amount_untaxed, 70000.0, 2)

        retention = line.od19_retention_id
        self.assertTrue(retention)
        self.assertEqual(retention.state, "held")
        self.assertAlmostEqual(retention.retention_amount, 53500.0, 2)

        hold = retention.move_id
        self.assertTrue(hold)
        self.assertEqual(hold.state, "posted")
        trade_receivable = self.customer.property_account_receivable_id
        retention_debit = sum(
            hold.line_ids.filtered(
                lambda line: line.account_id == self.retention_account
            ).mapped("debit")
        )
        trade_credit = sum(
            hold.line_ids.filtered(
                lambda line: line.account_id == trade_receivable
            ).mapped("credit")
        )
        self.assertAlmostEqual(retention_debit, 53500.0, 2)
        self.assertAlmostEqual(trade_credit, 53500.0, 2)

    def test_release_then_close(self):
        contract = self._make_contract()
        invoice = self._make_invoice(amount=1000000.0)
        line = self._link_billing_line(contract, invoice)
        invoice.action_post()
        retention = line.od19_retention_id
        self.assertEqual(retention.state, "held")

        retention.action_release()
        self.assertEqual(retention.state, "released")
        self.assertTrue(retention.released_date)
        self.assertTrue(retention.release_move_id)
        self.assertEqual(retention.release_move_id.state, "posted")

        retention.action_close()
        self.assertEqual(retention.state, "closed")

    def test_no_retention_created_when_rate_is_zero(self):
        contract = self._make_contract(rate=0.0)
        invoice = self._make_invoice(amount=1000000.0)
        line = self._link_billing_line(contract, invoice)
        self.assertFalse(line.od19_retention_rate)

        invoice.action_post()

        self.assertEqual(invoice.state, "posted")
        self.assertFalse(line.od19_retention_id)

    def test_release_date_derives_from_contract_days(self):
        contract = self._make_contract(days=30)
        invoice = self._make_invoice(amount=1000000.0)
        line = self._link_billing_line(contract, invoice)
        invoice.action_post()
        retention = line.od19_retention_id
        expected = fields.Date.add(invoice.invoice_date, days=30)
        self.assertEqual(retention.release_date, expected)

    def test_hold_blocked_when_retention_account_equals_trade_receivable(self):
        contract = self._make_contract()
        contract.od19_retention_account_id = (
            self.customer.property_account_receivable_id
        )
        retention = self.env["od19.sales.retention"].create(
            {
                "contract_id": contract.id,
                "partner_id": self.customer.id,
                "retention_rate": 5.0,
                "retention_amount": 53500.0,
            }
        )
        with self.assertRaises(UserError):
            retention.action_hold()
        self.assertEqual(retention.state, "draft")

    def test_overdue_flag_when_past_release_date(self):
        contract = self._make_contract()
        retention = self.env["od19.sales.retention"].create(
            {
                "contract_id": contract.id,
                "partner_id": self.customer.id,
                "retention_rate": 5.0,
                "retention_amount": 53500.0,
                "release_date": fields.Date.subtract(
                    fields.Date.context_today(self), days=1
                ),
                "state": "held",
            }
        )
        retention.invalidate_recordset()
        self.assertTrue(retention.is_overdue)
