# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestClearingWizards(AccountTestInvoicingCommon):
    """ทดสอบ wizard กระทบยอดเฉพาะทาง (VAT / WHT / Suspense)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        account_model = cls.env["account.account"]
        cls.vat_output = account_model.create(
            {
                "name": "Output VAT Test (ภาษีขาย)",
                "code": "999400",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )
        cls.vat_input = account_model.create(
            {
                "name": "Input VAT Test (ภาษีซื้อ)",
                "code": "999401",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.vat_payable = account_model.create(
            {
                "name": "VAT Payable Test",
                "code": "999402",
                "account_type": "liability_current",
            }
        )
        cls.vat_refund = account_model.create(
            {
                "name": "VAT Refundable Test",
                "code": "999403",
                "account_type": "asset_current",
            }
        )
        cls.wht_account = account_model.create(
            {
                "name": "WHT Payable Test",
                "code": "999404",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        cls.wht_remit = account_model.create(
            {
                "name": "WHT to Remit Test",
                "code": "999405",
                "account_type": "liability_current",
            }
        )
        cls.suspense_account = account_model.create(
            {
                "name": "Suspense Test",
                "code": "999406",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.misc_journal = cls.company_data["default_journal_misc"]
        cls.counter_account = cls.company_data["default_account_expense"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_move(self, account, debit=0.0, credit=0.0, date="2026-01-15"):
        """Post a balanced move touching ``account`` opposite the expense."""
        move = self.env["account.move"].create(
            {
                "journal_id": self.misc_journal.id,
                "date": date,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Clearing Test",
                            "account_id": account.id,
                            "debit": debit,
                            "credit": credit,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Clearing Test",
                            "account_id": self.counter_account.id,
                            "debit": credit,
                            "credit": debit,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def _open_lines(self, account):
        self.env.flush_all()
        return self.env["account.move.line"].search(
            [
                ("account_id", "=", account.id),
                ("parent_state", "=", "posted"),
                ("reconciled", "=", False),
            ]
        )

    def _account_balance(self, account):
        self.env.flush_all()
        lines = self.env["account.move.line"].search(
            [("account_id", "=", account.id), ("parent_state", "=", "posted")]
        )
        return sum(lines.mapped("balance"))

    def _vat_wizard(self, **overrides):
        vals = {
            "company_id": self.env.company.id,
            "date_to": "2026-01-31",
            "output_vat_account_ids": [(6, 0, [self.vat_output.id])],
            "input_vat_account_ids": [(6, 0, [self.vat_input.id])],
            "settlement_account_id": self.vat_payable.id,
            "refund_account_id": self.vat_refund.id,
        }
        vals.update(overrides)
        return self.env["od19.account.vat.clear.wizard"].create(vals)

    def _wht_wizard(self, **overrides):
        vals = {
            "company_id": self.env.company.id,
            "date_to": "2026-01-31",
            "wht_account_ids": [(6, 0, [self.wht_account.id])],
            "settlement_account_id": self.wht_remit.id,
        }
        vals.update(overrides)
        return self.env["od19.account.wht.clear.wizard"].create(vals)

    # ------------------------------------------------------------------
    # VAT Clearing (ภ.พ.30)
    # ------------------------------------------------------------------
    def test_vat_net_payable_settlement_and_reconcile(self):
        output_move = self._make_move(self.vat_output, credit=107.0)
        input_move = self._make_move(self.vat_input, debit=100.0)

        wizard = self._vat_wizard()
        self.assertAlmostEqual(wizard.output_vat_balance, 107.0)
        self.assertAlmostEqual(wizard.input_vat_balance, 100.0)
        self.assertAlmostEqual(wizard.net_vat_amount, 7.0)
        self.assertEqual(wizard.net_vat_type, "payable")

        wizard.action_load()
        wizard.action_clear()

        # Control accounts are cleared and fully reconciled.
        output_lines = output_move.line_ids.filtered(
            lambda line: line.account_id == self.vat_output
        )
        input_lines = input_move.line_ids.filtered(
            lambda line: line.account_id == self.vat_input
        )
        self.assertTrue(output_lines.reconciled)
        self.assertTrue(input_lines.reconciled)
        self.assertTrue(not self._open_lines(self.vat_output))
        self.assertTrue(not self._open_lines(self.vat_input))
        # Net payable transferred to the VAT payable account.
        self.assertAlmostEqual(self._account_balance(self.vat_payable), -7.0)

    def test_vat_net_refundable(self):
        self._make_move(self.vat_output, credit=100.0)
        self._make_move(self.vat_input, debit=107.0)

        wizard = self._vat_wizard()
        self.assertAlmostEqual(wizard.net_vat_amount, -7.0)
        self.assertEqual(wizard.net_vat_type, "refundable")

        wizard.action_load()
        wizard.action_clear()

        self.assertTrue(not self._open_lines(self.vat_output))
        self.assertTrue(not self._open_lines(self.vat_input))
        self.assertAlmostEqual(self._account_balance(self.vat_refund), 7.0)

    def test_vat_requires_settlement_account(self):
        self._make_move(self.vat_output, credit=107.0)
        self._make_move(self.vat_input, debit=100.0)

        wizard = self._vat_wizard(settlement_account_id=False)
        wizard.action_load()
        with self.assertRaises(UserError):
            wizard.action_clear()

    # ------------------------------------------------------------------
    # WHT Clearing
    # ------------------------------------------------------------------
    def test_wht_settlement_and_reconcile(self):
        wht_move = self._make_move(self.wht_account, credit=300.0)

        wizard = self._wht_wizard()
        self.assertAlmostEqual(wizard.wht_balance, 300.0)

        wizard.action_load()
        wizard.action_clear()

        wht_lines = wht_move.line_ids.filtered(
            lambda line: line.account_id == self.wht_account
        )
        self.assertTrue(wht_lines.reconciled)
        self.assertTrue(not self._open_lines(self.wht_account))
        self.assertAlmostEqual(self._account_balance(self.wht_remit), -300.0)

    def test_wht_settlement_disabled_reconciles_only(self):
        self._make_move(self.wht_account, credit=100.0)
        self._make_move(self.wht_account, debit=100.0)

        move_count = self.env["account.move"].search_count([])
        wizard = self._wht_wizard(od19_post_settlement=False)
        wizard.action_load()
        wizard.action_clear()

        self.assertEqual(self.env["account.move"].search_count([]), move_count)
        self.assertTrue(not self._open_lines(self.wht_account))
        self.assertAlmostEqual(self._account_balance(self.wht_remit), 0.0)

    def test_wht_requires_settlement_account(self):
        self._make_move(self.wht_account, credit=300.0)

        wizard = self._wht_wizard(settlement_account_id=False)
        wizard.action_load()
        with self.assertRaises(UserError):
            wizard.action_clear()

    # ------------------------------------------------------------------
    # Suspense / Intercompany Clearing
    # ------------------------------------------------------------------
    def test_suspense_reconciles_without_settlement(self):
        self._make_move(self.suspense_account, debit=100.0)
        self._make_move(self.suspense_account, credit=100.0)

        move_count = self.env["account.move"].search_count([])
        wizard = self.env["od19.account.suspense.clear.wizard"].create(
            {
                "company_id": self.env.company.id,
                "date_to": "2026-01-31",
                "suspense_account_ids": [(6, 0, [self.suspense_account.id])],
            }
        )
        wizard.action_load()
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_clear()

        # Reconcile only, no settlement entry created.
        self.assertEqual(self.env["account.move"].search_count([]), move_count)
        self.assertTrue(not self._open_lines(self.suspense_account))
