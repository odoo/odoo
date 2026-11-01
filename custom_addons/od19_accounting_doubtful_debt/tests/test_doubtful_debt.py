from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


# ``res.partner`` carries fields made required by other installed modules (for
# instance ``group_rfq`` from ``purchase_stock``). While this module is being
# installed the registry does not carry them yet, so the class runs during
# ``post_install`` where the registry is complete.
@tagged("post_install", "-at_install")
class TestDoubtfulDebt(TransactionCase):
    """Tests for the doubtful debt (หนี้สงสัยจะสูญ) workflow.

    Acceptance criteria (Wave 6.2 / WS-06):

    * an aging-bucket schedule can be configured per company and drives the
      provision rate applied to each open receivable;
    * a provision document computes the allowance from the *actual* open
      receivables and posts Dr expense / Cr allowance;
    * a write-off can only be posted after it has been approved by an
      Accounting Manager **and** carries at least one attached evidence;
    * posting a write-off clears the receivable (reconciles) it against.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Make sure the test user can approve write-offs.
        cls.env.user.write(
            {
                "group_ids": [
                    Command.link(cls.env.ref("account.group_account_manager").id)
                ]
            }
        )

        cls.expense_account = cls.env["account.account"].create(
            {
                "name": "Doubtful Debt Expense TEST",
                "code": "599101",
                "account_type": "expense",
            }
        )
        cls.allowance_account = cls.env["account.account"].create(
            {
                "name": "Doubtful Debt Allowance TEST",
                "code": "129101",
                "account_type": "asset_current",
            }
        )
        cls.income_account = cls.env["account.account"].create(
            {
                "name": "Doubtful Debt Test Income",
                "code": "499101",
                "account_type": "income",
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Doubtful Debt Journal TEST",
                "code": "DDJT",
                "type": "general",
            }
        )
        cls.company.write(
            {
                "od19_doubtful_debt_expense_account_id": cls.expense_account.id,
                "od19_doubtful_debt_allowance_account_id": cls.allowance_account.id,
                "od19_doubtful_debt_journal_id": cls.journal.id,
                "od19_doubtful_debt_aging_line_ids": [
                    Command.create(
                        {
                            "name": "0-30 days",
                            "sequence": 10,
                            "from_days": 0,
                            "to_days": 30,
                            "provision_rate": 0.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": "31-90 days",
                            "sequence": 20,
                            "from_days": 31,
                            "to_days": 90,
                            "provision_rate": 10.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Over 90 days",
                            "sequence": 30,
                            "from_days": 91,
                            "to_days": 0,
                            "provision_rate": 50.0,
                        }
                    ),
                ],
            }
        )
        cls.bucket_current = cls.company.od19_doubtful_debt_aging_line_ids.filtered(
            lambda b: b.from_days == 0
        )
        cls.bucket_31_90 = cls.company.od19_doubtful_debt_aging_line_ids.filtered(
            lambda b: b.from_days == 31
        )
        cls.bucket_over_90 = cls.company.od19_doubtful_debt_aging_line_ids.filtered(
            lambda b: b.from_days == 91
        )

        cls.partner = cls.env["res.partner"].create(
            {"name": "Doubtful Debtor TEST", "is_company": True}
        )

        cls.invoice_old = cls._create_open_invoice(1000.0, 100)
        cls.invoice_recent = cls._create_open_invoice(2000.0, 45)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _create_open_invoice(cls, amount, days_ago):
        invoice_date = fields.Date.context_today(cls) - timedelta(days=days_ago)
        invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner.id,
                "invoice_date": invoice_date,
                "date": invoice_date,
                "invoice_date_due": invoice_date,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Doubtful debt test line",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": cls.income_account.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _receivable_line(self, invoice):
        return invoice.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )

    def _make_provision(self):
        return self.env["od19.doubtful.debt.provision"].create(
            {
                "date": fields.Date.context_today(self),
                "company_id": self.company.id,
                "journal_id": self.journal.id,
                "expense_account_id": self.expense_account.id,
                "allowance_account_id": self.allowance_account.id,
            }
        )

    def _make_writeoff(self):
        ar_line = self._receivable_line(self.invoice_old)
        return self.env["od19.doubtful.debt.writeoff"].create(
            {
                "date": fields.Date.context_today(self),
                "company_id": self.company.id,
                "journal_id": self.journal.id,
                "expense_account_id": self.expense_account.id,
                "partner_id": self.partner.id,
                "reason": "ลูกหนี้เลิกกิจการ ค้นหาตัวไม่พบ",
                "reference": "ฎ.186 (2534)",
                "line_ids": [
                    Command.create(
                        {
                            "move_line_id": ar_line.id,
                            "amount": ar_line.amount_residual,
                        }
                    )
                ],
            }
        )

    def _attach_evidence(self, writeoff):
        return self.env["ir.attachment"].create(
            {
                "name": "writeoff_evidence.txt",
                "res_model": writeoff._name,
                "res_id": writeoff.id,
                "datas": "ZG91YnRmdWwgZGVidCBldmlkZW5jZQ==",
            }
        )

    # ------------------------------------------------------------------
    # Aging bucket configuration
    # ------------------------------------------------------------------
    def test_aging_bucket_validation(self):
        with self.assertRaises(ValidationError):
            self.env["od19.doubtful.debt.aging.line"].create(
                {
                    "name": "Invalid bucket",
                    "from_days": 100,
                    "to_days": 10,
                    "provision_rate": 5.0,
                    "company_id": self.company.id,
                }
            )

    def test_aging_bucket_match(self):
        self.assertTrue(self.bucket_current._od19_match(0))
        self.assertTrue(self.bucket_current._od19_match(30))
        self.assertFalse(self.bucket_current._od19_match(31))
        self.assertTrue(self.bucket_31_90._od19_match(45))
        # ``to_days = 0`` means "no upper bound" (last bucket).
        self.assertTrue(self.bucket_over_90._od19_match(5000))

    # ------------------------------------------------------------------
    # Provision
    # ------------------------------------------------------------------
    def test_provision_computed_from_open_receivables(self):
        provision = self._make_provision()
        provision.action_compute()

        old_line = provision.line_ids.filtered(
            lambda line: line.partner_id == self.partner
            and line.aging_line_id == self.bucket_over_90
        )
        self.assertEqual(len(old_line), 1)
        self.assertAlmostEqual(old_line.balance, 1000.0, 2)
        self.assertAlmostEqual(old_line.provision_rate, 50.0, 2)
        self.assertAlmostEqual(old_line.provision_amount, 500.0, 2)

        recent_line = provision.line_ids.filtered(
            lambda line: line.partner_id == self.partner
            and line.aging_line_id == self.bucket_31_90
        )
        self.assertEqual(len(recent_line), 1)
        self.assertAlmostEqual(recent_line.balance, 2000.0, 2)
        self.assertAlmostEqual(recent_line.provision_amount, 200.0, 2)

        self.assertAlmostEqual(
            sum(
                provision.line_ids.filtered(
                    lambda line: line.partner_id == self.partner
                ).mapped("provision_amount")
            ),
            700.0,
            2,
        )

    def test_provision_post_creates_balanced_move(self):
        provision = self._make_provision()
        provision.action_compute()
        total = provision.total_provision_amount
        self.assertGreaterEqual(total, 700.0 - 0.01)

        provision.action_post()

        self.assertEqual(provision.state, "posted")
        move = provision.move_id
        self.assertTrue(move)
        self.assertEqual(move.state, "posted")

        expense_debit = sum(
            move.line_ids.filtered(
                lambda line: line.account_id == self.expense_account
            ).mapped("debit")
        )
        allowance_credit = sum(
            move.line_ids.filtered(
                lambda line: line.account_id == self.allowance_account
            ).mapped("credit")
        )
        self.assertAlmostEqual(expense_debit, total, 2)
        self.assertAlmostEqual(allowance_credit, total, 2)
        self.assertAlmostEqual(sum(move.line_ids.mapped("debit")), sum(move.line_ids.mapped("credit")), 2)

    def test_provision_action_post_requires_lines(self):
        provision = self._make_provision()
        with self.assertRaises(UserError):
            provision.action_post()

    # ------------------------------------------------------------------
    # Write-off
    # ------------------------------------------------------------------
    def test_writeoff_requires_approval_before_post(self):
        writeoff = self._make_writeoff()
        self.assertEqual(writeoff.state, "draft")
        with self.assertRaises(UserError):
            writeoff.action_post()

    def test_writeoff_approval_requires_account_manager(self):
        writeoff = self._make_writeoff()
        normal_user = self.env["res.users"].create(
            {
                "name": "dd_normal_user",
                "login": "dd_normal_user",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_user").id,
                        ]
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            writeoff.with_user(normal_user).action_approve()
        self.assertEqual(writeoff.state, "draft")

    def test_writeoff_requires_evidence_then_posts_and_reconciles(self):
        writeoff = self._make_writeoff()
        ar_line = self._receivable_line(self.invoice_old)
        writeoff.action_approve()
        self.assertEqual(writeoff.state, "approved")
        self.assertEqual(writeoff.approver_id, self.env.user)

        # No evidence attached yet -> posting must be blocked.
        with self.assertRaises(UserError):
            writeoff.action_post()

        self._attach_evidence(writeoff)
        writeoff.invalidate_recordset(["evidence_count"])
        self.assertEqual(writeoff.evidence_count, 1)

        writeoff.action_post()

        self.assertEqual(writeoff.state, "posted")
        move = writeoff.move_id
        self.assertTrue(move)
        self.assertEqual(move.state, "posted")

        # GL: Dr bad debt expense / Cr receivable, balanced.
        expense_debit = sum(
            move.line_ids.filtered(
                lambda line: line.account_id == self.expense_account
            ).mapped("debit")
        )
        self.assertAlmostEqual(expense_debit, writeoff.total_amount, 2)
        self.assertAlmostEqual(
            sum(move.line_ids.mapped("debit")),
            sum(move.line_ids.mapped("credit")),
            2,
        )

        # The original receivable line must be fully cleared.
        ar_line.invalidate_recordset()
        self.assertTrue(ar_line.reconciled)
        self.assertAlmostEqual(ar_line.amount_residual, 0.0, 2)
