import logging

from odoo.tests import tagged

from .common import TestPoSCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPosSessionChallenge(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def _close_bank_sales(self, sale_amounts, difference, method=None):
        method = method or self.bank_pm1
        session = self._start_pos_session(method, 0)
        product = self.create_product("Bank challenge", self.categ_basic, 100, 50)
        self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(product, amount / 100)],
                    "payments": [(method, amount)],
                    "customer": self.customer,
                    "uuid": f"bank-challenge-{session.id}-{index}",
                }
                for index, amount in enumerate(sale_amounts)
            ]
        )
        session.action_pos_session_closing_control(
            bank_payment_method_diffs={method.id: difference}
        )
        return session

    def _assert_counted_bank(self, session, expected, difference, method=None):
        method = method or self.bank_pm1
        payments = session.bank_payment_ids
        bank_lines = session._get_related_account_moves().line_ids.filtered(
            lambda line: line.account_id == method.outstanding_account_id
        )
        _logger.debug(
            "Bank posting payments=%s directions=%s balances=%s",
            payments.ids,
            payments.mapped("payment_type"),
            bank_lines.mapped("balance"),
        )
        self.assertEqual(sum(bank_lines.mapped("balance")), expected + difference)
        if payments:
            receivable_account = (
                self.customer.property_account_receivable_id
                if method.split_transactions
                else self.pos_receivable_bank
            )
            receivable_lines = (session.move_id | payments.move_id).line_ids.filtered(
                lambda line: line.account_id == receivable_account
            )
            self.assertEqual(sum(receivable_lines.mapped("balance")), 0)
            self.assertTrue(all(receivable_lines.mapped("reconciled")))
        report = self.env["report.point_of_sale.report_saledetails"].get_sale_details(
            session_ids=session.ids
        )
        rows = [row for row in report["payments"] if row.get("id") == method.id]
        _logger.debug(
            "Bank challenge expected=%s difference=%s rows=%s",
            expected,
            difference,
            rows,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["final_count"], expected)
        self.assertEqual(rows[0]["money_counted"], expected + difference)
        self.assertEqual(rows[0]["money_difference"], difference)
        return rows[0]

    def test_zero_net_captured_bank_payments_keep_difference(self):
        session = self._close_bank_sales([100, -100], 20)
        self.assertEqual(session.state, "closed")
        self._assert_counted_bank(session, 0, 20)
        self.assertFalse(
            self.env["account.move"].search(
                [
                    ("pos_diff_session_id", "=", session.id),
                ]
            ),
            "A combined adjustment must not also create a standalone difference",
        )

    def test_combined_bank_difference_crossing_zero_keeps_signed_count(self):
        for expected, difference in (
            (10, -20),
            (-10, 20),
            (-10, -5),
            (10, 5),
            (-10, 0),
            (10, -10),
            (-10, 10),
        ):
            with (
                self.subTest(expected=expected, difference=difference),
                self.env.cr.savepoint(),
            ):
                session = self._close_bank_sales([expected], difference)
                self.assertEqual(session.state, "closed")
                self._assert_counted_bank(session, expected, difference)

    def test_shared_profit_and_loss_account_keeps_gain_sign(self):
        self.bank_pm1.journal_id.loss_account_id = (
            self.bank_pm1.journal_id.profit_account_id
        )
        session = self._close_bank_sales([], 20)
        self._assert_counted_bank(session, 0, 20)

    def test_split_bank_refund_keeps_bank_and_receivable_roles(self):
        session = self._close_bank_sales([-10], 20, self.bank_split_pm1)
        self._assert_counted_bank(session, -10, 20, self.bank_split_pm1)

    def test_unused_bank_method_uses_same_default_account_as_captured_payments(self):
        self.bank_pm1.outstanding_account_id = False
        for sign in (1, -1):
            with self.subTest(sign=sign), self.env.cr.savepoint():
                captured = self._close_bank_sales([100 * sign], 20 * sign)
                expected_account = captured.bank_payment_ids.outstanding_account_id
                self.assertTrue(expected_account)
                _logger.debug(
                    "Captured bank payment sign=%s resolved default account=%s",
                    sign,
                    expected_account,
                )

                empty = self._close_bank_sales([], 20 * sign)

                moves = self.env["account.move"].search(
                    [("pos_diff_session_id", "=", empty.id)]
                )
                lines = moves.line_ids.filtered(
                    lambda line, account=expected_account: line.account_id == account
                )
                self.assertEqual(sum(lines.mapped("balance")), 20 * sign)
                self.assertEqual(moves.state, "posted")
                self.assertFalse(empty.bank_payment_ids)
