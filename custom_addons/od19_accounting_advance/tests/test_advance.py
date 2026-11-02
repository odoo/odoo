from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAdvance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer_advance_account = cls.env["account.account"].create(
            {
                "name": "Customer Advance",
                "code": "214001",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )
        cls.supplier_advance_account = cls.env["account.account"].create(
            {
                "name": "Supplier Advance",
                "code": "121001",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.cash_account = cls.env["account.account"].create(
            {
                "name": "Cash",
                "code": "111001",
                "account_type": "asset_cash",
            }
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Test Customer", "is_company": True}
        )
        cls.supplier = cls.env["res.partner"].create(
            {"name": "Test Supplier", "is_company": True}
        )
        cls.customer_journal = cls.env["account.journal"].create(
            {
                "name": "Customer Advance Journal",
                "type": "general",
                "code": "CADV",
                "default_account_id": cls.cash_account.id,
            }
        )
        cls.supplier_journal = cls.env["account.journal"].create(
            {
                "name": "Supplier Advance Journal",
                "type": "general",
                "code": "SADV",
                "default_account_id": cls.cash_account.id,
            }
        )
        cls.vat_account = cls.env["account.account"].create(
            {
                "name": "Output VAT",
                "code": "215001",
                "account_type": "liability_current",
            }
        )
        cls.wht_account = cls.env["account.account"].create(
            {
                "name": "WHT Payable",
                "code": "216001",
                "account_type": "liability_current",
                "wht_account": True,
            }
        )
        cls.sale_tax = cls.env["account.tax"].create(
            {
                "name": "VAT 7%",
                "amount": 7.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        cls.sale_tax.invoice_repartition_line_ids.filtered(
            lambda line: line.repartition_type == "tax"
        ).account_id = cls.vat_account
        cls.wht_tax = cls.env["account.withholding.tax"].create(
            {
                "name": "WHT 3% Services",
                "account_id": cls.wht_account.id,
                "amount": 3.0,
            }
        )

    def _create_customer_advance(self, kind, amount=100000.0, **kwargs):
        vals = {
            "advance_type": "customer",
            "partner_id": self.customer.id,
            "amount": amount,
            "date": "2024-01-15",
            "advance_account_id": self.customer_advance_account.id,
            "journal_id": self.customer_journal.id,
            "od19_advance_kind": kind,
        }
        vals.update(kwargs)
        return self.env["account.advance"].create(vals)

    def test_create_customer_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 50000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
            }
        )
        self.assertEqual(advance.state, "draft")
        self.assertEqual(advance.remaining_amount, 50000.0)
        self.assertEqual(advance.used_amount, 0.0)

    def test_create_supplier_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "supplier",
                "partner_id": self.supplier.id,
                "amount": 30000.0,
                "date": "2024-01-15",
                "advance_account_id": self.supplier_advance_account.id,
            }
        )
        self.assertEqual(advance.state, "draft")
        self.assertEqual(advance.remaining_amount, 30000.0)

    def test_post_customer_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 50000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
                "journal_id": self.customer_journal.id,
            }
        )
        advance.action_post()
        self.assertEqual(advance.state, "posted")
        self.assertTrue(advance.move_id)

    def test_post_supplier_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "supplier",
                "partner_id": self.supplier.id,
                "amount": 30000.0,
                "date": "2024-01-15",
                "advance_account_id": self.supplier_advance_account.id,
                "journal_id": self.supplier_journal.id,
            }
        )
        advance.action_post()
        self.assertEqual(advance.state, "posted")
        self.assertTrue(advance.move_id)

    def test_advance_requires_positive_amount(self):
        with self.assertRaises(ValidationError):
            self.env["account.advance"].create(
                {
                    "advance_type": "customer",
                    "partner_id": self.customer.id,
                    "amount": -100.0,
                    "date": "2024-01-15",
                    "advance_account_id": self.customer_advance_account.id,
                }
            )

    def test_cancel_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 50000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
                "journal_id": self.customer_journal.id,
            }
        )
        advance.action_post()
        advance.action_cancel()
        self.assertEqual(advance.state, "cancel")

    def test_cannot_cancel_draft(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 50000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
            }
        )
        with self.assertRaises(ValidationError):
            advance.action_cancel()

    def _create_posted_customer_advance(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 50000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
                "journal_id": self.customer_journal.id,
            }
        )
        advance.action_post()
        return advance

    def _create_application_move(self, account, partner):
        """Entry that consumes the advance: Dr advance account / Cr cash."""
        move = self.env["account.move"].create(
            {
                "journal_id": self.customer_journal.id,
                "date": "2024-01-20",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": account.id,
                            "partner_id": partner.id,
                            "debit": 50000.0,
                            "credit": 0.0,
                            "name": "Apply advance",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": self.cash_account.id,
                            "partner_id": partner.id,
                            "debit": 0.0,
                            "credit": 50000.0,
                            "name": "Apply advance",
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def test_action_reconcile_customer_advance_sets_reconciled(self):
        advance = self._create_posted_customer_advance()
        self._create_application_move(self.customer_advance_account, self.customer)

        advance.action_reconcile()

        self.assertEqual(advance.state, "reconciled")
        self.assertEqual(advance.remaining_amount, 0.0)
        advance_line = advance.move_id.line_ids.filtered(
            lambda line: line.account_id == self.customer_advance_account
        )
        self.assertTrue(advance_line.reconciled)

    def test_action_reconcile_without_counterpart_stays_posted(self):
        advance = self._create_posted_customer_advance()

        advance.action_reconcile()

        self.assertEqual(advance.state, "posted")
        self.assertEqual(advance.remaining_amount, 50000.0)

    def _assert_balanced(self, move):
        self.assertAlmostEqual(
            sum(move.line_ids.mapped("debit")),
            sum(move.line_ids.mapped("credit")),
            2,
        )

    def test_advance_kind_defaults_to_prepayment(self):
        advance = self.env["account.advance"].create(
            {
                "advance_type": "customer",
                "partner_id": self.customer.id,
                "amount": 1000.0,
                "date": "2024-01-15",
                "advance_account_id": self.customer_advance_account.id,
            }
        )
        self.assertEqual(advance.od19_advance_kind, "prepayment")
        self.assertEqual(advance.od19_tax_amount, 0.0)
        self.assertEqual(advance.od19_total_amount, 1000.0)

    def test_customer_deposit_applies_output_vat(self):
        """รับมัดจำ 100,000 -> ใบกำกับ/รายการ 107,000 (VAT 7,000)."""
        advance = self._create_customer_advance(
            "deposit", od19_tax_id=self.sale_tax.id
        )
        self.assertEqual(advance.od19_tax_amount, 7000.0)
        self.assertEqual(advance.od19_total_amount, 107000.0)

        advance.action_post()

        self.assertEqual(advance.state, "posted")
        move = advance.move_id
        self._assert_balanced(move)
        vat_line = move.line_ids.filtered(
            lambda line: line.account_id == self.vat_account
        )
        self.assertAlmostEqual(vat_line.credit, 7000.0, 2)
        self.assertAlmostEqual(vat_line.debit, 0.0, 2)
        cash_line = move.line_ids.filtered(
            lambda line: line.account_id == self.cash_account
        )
        self.assertAlmostEqual(cash_line.debit, 107000.0, 2)

    def test_security_deposit_has_no_output_vat(self):
        """เงินประกันที่ต้องคืน ไม่เกิดภาษีขาย แม้จะเลือกภาษีไว้."""
        advance = self._create_customer_advance(
            "security", od19_tax_id=self.sale_tax.id
        )
        self.assertEqual(advance.od19_tax_amount, 0.0)
        self.assertEqual(advance.od19_total_amount, 100000.0)

        advance.action_post()

        move = advance.move_id
        self._assert_balanced(move)
        self.assertFalse(
            move.line_ids.filtered(lambda line: line.account_id == self.vat_account)
        )

    def test_supplier_prepayment_applies_wht(self):
        """จ่ายล่วงหน้าผู้ขาย (ค่าบริการ) หัก WHT 3% -> จ่ายสุทธิ 97,000."""
        advance = self.env["account.advance"].create(
            {
                "advance_type": "supplier",
                "partner_id": self.supplier.id,
                "amount": 100000.0,
                "date": "2024-01-15",
                "advance_account_id": self.supplier_advance_account.id,
                "journal_id": self.supplier_journal.id,
                "od19_advance_kind": "prepayment",
                "od19_wht_tax_id": self.wht_tax.id,
            }
        )
        self.assertEqual(advance.od19_wht_amount, 3000.0)
        self.assertEqual(advance.od19_total_amount, 100000.0)

        advance.action_post()

        move = advance.move_id
        self._assert_balanced(move)
        wht_line = move.line_ids.filtered(
            lambda line: line.account_id == self.wht_account
        )
        self.assertAlmostEqual(wht_line.credit, 3000.0, 2)
        cash_line = move.line_ids.filtered(
            lambda line: line.account_id == self.cash_account
        )
        self.assertAlmostEqual(cash_line.credit, 97000.0, 2)

    def test_wht_ignored_for_customer_advance(self):
        advance = self._create_customer_advance(
            "prepayment", od19_wht_tax_id=self.wht_tax.id
        )
        self.assertEqual(advance.od19_wht_amount, 0.0)
