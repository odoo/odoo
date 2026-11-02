# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


@tagged("od19_accounting_dncn")
class TestDNCN(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.product = cls.env["product.product"].create({
            "name": "Test Product",
            "type": "service",
            "list_price": 100,
        })
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.reason = cls.env["account.move.dncn.reason"].create({
            "name": "Test Reason",
        })

    def _create_invoice(self):
        return self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 100,
            })],
        })

    def test_dn_requires_reason(self):
        invoice = self._create_invoice()
        invoice.action_post()
        # Create DN without reason
        dn = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "dncn": "dn",
            "parent_id": invoice.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 50,
            })],
        })
        with self.assertRaises(ValidationError):
            dn.action_post()

    def test_dn_with_reason_posts(self):
        invoice = self._create_invoice()
        invoice.action_post()
        dn = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "dncn": "dn",
            "parent_id": invoice.id,
            "reason_id": self.reason.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 50,
            })],
        })
        dn.action_post()
        self.assertEqual(dn.state, "posted")

    def test_credit_note_sets_reversed_entry(self):
        invoice = self._create_invoice()
        invoice.action_post()
        action = invoice.action_create_credit_note()
        ctx = action["context"]
        self.assertEqual(ctx.get("default_dncn"), "cn")
        self.assertEqual(ctx.get("default_parent_id"), invoice.id)
        self.assertEqual(ctx.get("default_reversed_entry_id"), invoice.id)

    def test_remaster_invoice_copies_lines(self):
        invoice = self._create_invoice()
        invoice.action_post()
        action = invoice.action_remaster_invoice()
        remaster = self.env["account.move"].browse(action["res_id"])
        self.assertEqual(remaster.dncn, "re")
        self.assertEqual(remaster.parent_id, invoice)
        self.assertEqual(len(remaster.invoice_line_ids), 1)
        self.assertEqual(remaster.invoice_line_ids.price_unit, 100)

    def _create_credit_note(self, invoice, price_unit=100):
        return self.env["account.move"].create({
            "move_type": "out_refund",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "dncn": "cn",
            "parent_id": invoice.id,
            "reversed_entry_id": invoice.id,
            "reason_id": self.reason.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": price_unit,
            })],
        })

    def test_credit_note_reconciles_with_parent(self):
        invoice = self._create_invoice()
        invoice.action_post()
        cn = self._create_credit_note(invoice)

        cn.action_post()

        receivable = self.partner.property_account_receivable_id
        lines = (invoice.line_ids + cn.line_ids).filtered(
            lambda line: line.account_id == receivable
        )
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(lines.mapped("reconciled")))
        self.assertEqual(len(lines.mapped("full_reconcile_id")), 1)
        self.assertEqual(sum(lines.mapped("amount_residual")), 0.0)

    def test_debit_note_does_not_settle_parent(self):
        invoice = self._create_invoice()
        invoice.action_post()
        dn = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "dncn": "dn",
            "parent_id": invoice.id,
            "reason_id": self.reason.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 50,
            })],
        })

        dn.action_post()

        receivable = self.partner.property_account_receivable_id
        dn_line = dn.line_ids.filtered(lambda line: line.account_id == receivable)
        self.assertFalse(dn_line.reconciled)
