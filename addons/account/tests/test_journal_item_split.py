from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestJournalItemSplit(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.revenue = cls.company_data["default_account_revenue"]
        cls.expense = cls.company_data["default_account_expense"]

    def _draft_entry(self, balance=300.0):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2019-01-01",
                "line_ids": [
                    Command.create({"account_id": self.revenue.id, "balance": balance}),
                    Command.create(
                        {"account_id": self.expense.id, "balance": -balance}
                    ),
                ],
            }
        )
        return move, move.line_ids.filtered(lambda line: line.balance > 0)

    def _wizard(self, lines, **vals):
        action = lines.action_split_lines()
        return (
            self.env[action["res_model"]].with_context(**action["context"]).create(vals)
        )

    def test_split_one_line_into_three_keeps_the_move_balanced(self):
        move, line = self._draft_entry(300.0)

        self._wizard(line, quantity=3).split()

        split_lines = move.line_ids.filtered(lambda ml: ml.account_id == self.revenue)
        self.assertEqual(len(split_lines), 3)
        self.assertEqual(sum(split_lines.mapped("balance")), 300.0)
        self.assertRecordValues(
            split_lines.sorted("balance"),
            [{"balance": 100.0}, {"balance": 100.0}, {"balance": 100.0}],
        )
        # `_check_balanced` would have raised on flush if it were not.
        self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0)

    def test_split_into_two_puts_the_remainder_on_the_chosen_account(self):
        """The uneven split: the part peeled off must carry its own amount.

        This is the one that catches the `amount_currency` trap -- with only
        `balance` overridden, `copy_data` carries the source `amount_currency`
        and `_sync_dynamic_lines` re-derives `balance` from it, so 300 split
        into 180/120 comes back 180/180 and the move fails `_check_balanced`.
        """
        move, line = self._draft_entry(300.0)

        self._wizard(line, quantity=2, amount=120.0, account_id=self.expense.id).split()

        self.assertRecordValues(
            move.line_ids.filtered(lambda ml: ml.balance > 0).sorted("balance"),
            [
                {"balance": 120.0, "account_id": self.expense.id},
                {"balance": 180.0, "account_id": self.revenue.id},
            ],
        )
        self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0)

    def test_split_of_an_indivisible_amount_still_sums_to_the_original(self):
        """100 in 3 rounds the way the field would; the remainder rides the last part."""
        move, line = self._draft_entry(100.0)

        self._wizard(line, quantity=3).split()

        split_lines = move.line_ids.filtered(lambda ml: ml.account_id == self.revenue)
        self.assertEqual(len(split_lines), 3)
        self.assertEqual(sum(split_lines.mapped("balance")), 100.0)
        self.assertEqual(sum(move.line_ids.mapped("balance")), 0.0)

    def test_split_refuses_a_posted_move(self):
        move, line = self._draft_entry(300.0)
        move.action_post()

        with self.assertRaisesRegex(UserError, "draft"):
            self._wizard(line, quantity=2)

    def test_split_refuses_a_quantity_below_two(self):
        _move, line = self._draft_entry(300.0)

        with self.assertRaisesRegex(UserError, "greater than 1"):
            self._wizard(line, quantity=1).split()
