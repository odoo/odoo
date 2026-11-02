# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestReconcileAccountLines(AccountTestInvoicingCommon):
    """ทดสอบ helper กลาง ``_od19_reconcile_account_lines`` (ตัดบัญชี)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reconcile_account = cls.env["account.account"].create(
            {
                "name": "Reconcile Test Account",
                "code": "999100",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.non_reconcile_account = cls.env["account.account"].create(
            {
                "name": "Non Reconcile Test Account",
                "code": "999200",
                "account_type": "asset_current",
                "reconcile": False,
            }
        )
        cls.misc_journal = cls.company_data["default_journal_misc"]
        cls.counter_account = cls.company_data["default_account_expense"]

    def _create_move(self, lines):
        move = self.env["account.move"].create(
            {
                "journal_id": self.misc_journal.id,
                "date": "2026-01-01",
                "line_ids": [(0, 0, line) for line in lines],
            }
        )
        move.action_post()
        return move

    def _account_lines(self, *moves):
        self.env.flush_all()
        return (moves[0] + moves[1]).line_ids.filtered(
            lambda line: line.account_id == self.reconcile_account
        )

    def test_reconcile_account_lines_matches_partner_lines(self):
        partner = self.partner_a
        debit_move = self._create_move(
            [
                {"name": "A", "account_id": self.reconcile_account.id, "partner_id": partner.id, "debit": 100.0},
                {"name": "A", "account_id": self.counter_account.id, "partner_id": partner.id, "credit": 100.0},
            ]
        )
        credit_move = self._create_move(
            [
                {"name": "B", "account_id": self.reconcile_account.id, "partner_id": partner.id, "credit": 100.0},
                {"name": "B", "account_id": self.counter_account.id, "partner_id": partner.id, "debit": 100.0},
            ]
        )

        result = debit_move._od19_reconcile_account_lines(
            self.reconcile_account.id, partner.id
        )
        self.assertTrue(result)

        lines = self._account_lines(debit_move, credit_move)
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(lines.mapped("reconciled")))
        self.assertEqual(len(lines.mapped("full_reconcile_id")), 1)
        self.assertEqual(sum(lines.mapped("amount_residual")), 0.0)

    def test_reconcile_account_lines_skips_other_partner(self):
        debit_move = self._create_move(
            [
                {"name": "A", "account_id": self.reconcile_account.id, "partner_id": self.partner_a.id, "debit": 100.0},
                {"name": "A", "account_id": self.counter_account.id, "partner_id": self.partner_a.id, "credit": 100.0},
            ]
        )
        other_move = self._create_move(
            [
                {"name": "B", "account_id": self.reconcile_account.id, "partner_id": self.partner_b.id, "credit": 100.0},
                {"name": "B", "account_id": self.counter_account.id, "partner_id": self.partner_b.id, "debit": 100.0},
            ]
        )

        # Only one partner_a line exists -> nothing to match.
        self.assertFalse(
            debit_move._od19_reconcile_account_lines(
                self.reconcile_account.id, self.partner_a.id
            )
        )
        other_line = other_move.line_ids.filtered(
            lambda line: line.account_id == self.reconcile_account
        )
        self.assertFalse(other_line.reconciled)

    def test_reconcile_account_lines_ignores_non_reconcilable_account(self):
        move = self._create_move(
            [
                {"name": "A", "account_id": self.non_reconcile_account.id, "debit": 100.0},
                {"name": "A", "account_id": self.counter_account.id, "credit": 100.0},
            ]
        )
        self.assertFalse(
            move._od19_reconcile_account_lines(self.non_reconcile_account.id)
        )

    def _reconcile_partner_line(self, move, partner):
        self.env.flush_all()
        return move.line_ids.filtered(
            lambda line: line.account_id == self.reconcile_account
            and line.partner_id == partner
        )

    def test_reconcile_move_lines_matches_only_given_lines(self):
        partner = self.partner_a
        debit_move = self._create_move(
            [
                {"name": "A", "account_id": self.reconcile_account.id, "partner_id": partner.id, "debit": 100.0},
                {"name": "A", "account_id": self.counter_account.id, "partner_id": partner.id, "credit": 100.0},
            ]
        )
        credit_move = self._create_move(
            [
                {"name": "B", "account_id": self.reconcile_account.id, "partner_id": partner.id, "credit": 100.0},
                {"name": "B", "account_id": self.counter_account.id, "partner_id": partner.id, "debit": 100.0},
            ]
        )
        unrelated_move = self._create_move(
            [
                {"name": "C", "account_id": self.reconcile_account.id, "partner_id": partner.id, "credit": 40.0},
                {"name": "C", "account_id": self.counter_account.id, "partner_id": partner.id, "debit": 40.0},
            ]
        )

        debit_line = self._reconcile_partner_line(debit_move, partner)
        credit_line = self._reconcile_partner_line(credit_move, partner)
        unrelated_line = self._reconcile_partner_line(unrelated_move, partner)

        result = debit_move._od19_reconcile_move_lines(debit_line + credit_line)

        self.assertTrue(result)
        self.assertTrue(debit_line.reconciled)
        self.assertTrue(credit_line.reconciled)
        self.assertFalse(unrelated_line.reconciled)

    def test_reconcile_move_lines_needs_two_lines(self):
        partner = self.partner_a
        debit_move = self._create_move(
            [
                {"name": "A", "account_id": self.reconcile_account.id, "partner_id": partner.id, "debit": 100.0},
                {"name": "A", "account_id": self.counter_account.id, "partner_id": partner.id, "credit": 100.0},
            ]
        )
        debit_line = self._reconcile_partner_line(debit_move, partner)

        self.assertFalse(debit_move._od19_reconcile_move_lines(debit_line))
