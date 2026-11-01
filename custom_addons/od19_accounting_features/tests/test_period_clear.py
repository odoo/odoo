# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountPeriodClear(AccountTestInvoicingCommon):
    """ทดสอบ wizard กระทบยอดปิดงวด ``od19.account.period.clear.wizard``."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.control_account = cls.env["account.account"].create(
            {
                "name": "Period Clearing Control Test",
                "code": "999300",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.misc_journal = cls.company_data["default_journal_misc"]
        cls.counter_account = cls.company_data["default_account_expense"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _make_move(self, control_debit=0.0, control_credit=0.0, date="2026-01-15"):
        """Post a balanced move touching the control account."""
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
                            "account_id": self.control_account.id,
                            "debit": control_debit,
                            "credit": control_credit,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Clearing Test",
                            "account_id": self.counter_account.id,
                            "debit": control_credit,
                            "credit": control_debit,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def _wizard(self, date_from="2026-01-01", date_to="2026-01-31"):
        return self.env["od19.account.period.clear.wizard"].create(
            {
                "company_id": self.env.company.id,
                "date_from": date_from,
                "date_to": date_to,
                "account_ids": [(6, 0, [self.control_account.id])],
            }
        )

    def _control_lines(self, *moves):
        self.env.flush_all()
        lines = self.env["account.move.line"]
        for move in moves:
            lines |= move.line_ids.filtered(
                lambda line: line.account_id == self.control_account
            )
        return lines

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_default_accounts_are_eligible(self):
        wizard = self.env["od19.account.period.clear.wizard"].create(
            {
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
            }
        )
        self.assertIn(self.control_account, wizard.account_ids)

    def test_load_groups_open_items_by_account_and_partner(self):
        self._make_move(control_debit=100.0)
        self._make_move(control_credit=100.0)

        wizard = self._wizard()
        wizard.action_load()

        self.assertEqual(len(wizard.line_ids), 1)
        line = wizard.line_ids
        self.assertEqual(line.account_id, self.control_account)
        self.assertEqual(line.line_count, 2)
        self.assertAlmostEqual(line.debit, 100.0)
        self.assertAlmostEqual(line.credit, 100.0)
        self.assertAlmostEqual(line.balance, 0.0)

    def test_reconcile_clears_open_items(self):
        debit_move = self._make_move(control_debit=100.0)
        credit_move = self._make_move(control_credit=100.0)

        wizard = self._wizard()
        wizard.action_load()
        wizard.action_reconcile()

        control_lines = self._control_lines(debit_move, credit_move)
        self.assertEqual(len(control_lines), 2)
        self.assertTrue(all(control_lines.mapped("reconciled")))
        self.assertAlmostEqual(sum(control_lines.mapped("amount_residual")), 0.0)
        # Nothing left open -> the reloaded wizard is empty.
        self.assertFalse(wizard.line_ids)

    def test_out_of_period_items_are_not_loaded(self):
        self._make_move(control_debit=100.0, date="2025-12-15")

        wizard = self._wizard("2026-01-01", "2026-01-31")
        wizard.action_load()

        self.assertFalse(wizard.line_ids)

    def test_reconcile_does_not_touch_out_of_period_lines(self):
        in_period_debit = self._make_move(control_debit=100.0, date="2026-01-15")
        in_period_credit = self._make_move(control_credit=100.0, date="2026-01-20")
        out_of_period = self._make_move(control_debit=50.0, date="2025-12-15")

        wizard = self._wizard("2026-01-01", "2026-01-31")
        wizard.action_load()
        wizard.action_reconcile()

        self.assertTrue(
            all(self._control_lines(in_period_debit, in_period_credit).mapped("reconciled"))
        )
        out_line = self._control_lines(out_of_period)
        self.assertFalse(out_line.reconciled)
        self.assertAlmostEqual(out_line.amount_residual, 50.0)
