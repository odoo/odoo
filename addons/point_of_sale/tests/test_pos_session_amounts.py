import logging

from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from .common import TestPoSCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPosSessionAmounts(TestPoSCommon):
    invalid_amounts = (
        float("nan"),
        float("inf"),
        -float("inf"),
        10**400,
        True,
        "12.50",
    )

    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def _assert_rejected_without_rollback(self, operation, *args, **kwargs):
        # TransactionCase.assertRaises rolls back automatically. Catch the error
        # here so the assertions also detect writes performed before rejection.
        try:
            operation(*args, **kwargs)
        except UserError as error:
            _logger.debug("Amount rejected without rolling back: %s", error)
        else:
            self.fail("Invalid amount was accepted")
        self.env.flush_all()

    def test_cash_movements_refuse_non_numeric_or_non_finite_amounts(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        for amount in self.invalid_amounts:
            with self.subTest(amount=amount), self.env.cr.savepoint():
                _logger.debug("Cash movement rejects amount=%r", amount)
                self._assert_rejected_without_rollback(
                    session.try_cash_in_out, "in", amount, "Float", False, {}
                )
                self.assertFalse(session.statement_line_ids)

    def test_opening_count_refuses_invalid_amount_without_opening(self):
        self.config.payment_method_ids = self.cash_pm1
        self.config.open_ui()
        session = self.config.current_session_id
        for amount in self.invalid_amounts:
            with self.subTest(amount=amount), self.env.cr.savepoint():
                _logger.debug("Opening count rejects amount=%r", amount)
                self._assert_rejected_without_rollback(
                    session.set_opening_control, amount, "Counted"
                )
                self.assertEqual(session.state, "opening_control")
                self.assertEqual(session.cash_register_balance_start, 0)

    def test_closing_count_refuses_invalid_amount_without_changing_count(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        session.update_closing_cash_details(12.50)
        for amount in self.invalid_amounts:
            with self.subTest(amount=amount), self.env.cr.savepoint():
                _logger.debug("Closing count rejects amount=%r", amount)
                self._assert_rejected_without_rollback(
                    session.update_closing_cash_details, amount
                )
                self.assertEqual(session.cash_register_balance_end_real, 12.50)

    def test_bank_difference_refuses_integer_overflow_as_user_error(self):
        session = self._start_pos_session(self.bank_pm1, 0)
        _logger.debug("Closing refuses overflowing bank difference")
        self._assert_rejected_without_rollback(
            session.action_pos_session_close,
            bank_payment_method_diffs={self.bank_pm1.id: 10**400},
        )
        self.assertEqual(session.state, "opened")

    def test_fractional_counts_and_signed_cash_movements_still_work(self):
        self.config.payment_method_ids = self.cash_pm1
        self.config.open_ui()
        session = self.config.current_session_id
        session.set_opening_control(12.50, "Counted")
        session.try_cash_in_out("out", -2.25, "Petty cash", False, {})
        session.update_closing_cash_details(10.25)
        _logger.debug(
            "Fractional drawer expected=%s counted=%s",
            session.cash_register_balance_end,
            session.cash_register_balance_end_real,
        )
        self.assertEqual(session.cash_register_balance_end, 10.25)
        self.assertEqual(session.cash_register_difference, 0)

    def test_cashier_can_count_open_and_close_with_idempotent_opening(self):
        cashier = new_test_user(
            self.env,
            login="session_amount_cashier",
            groups="base.group_user,point_of_sale.group_pos_user",
            company_id=self.company.id,
        )
        self.config.payment_method_ids = self.cash_pm1
        self.config.open_ui()
        session = self.config.current_session_id.with_user(cashier)

        session.set_opening_control(12.50, "First opening")
        started = session.start_at
        session.set_opening_control(99, "Repeated opening")
        self.assertEqual(session.cash_register_balance_start, 12.50)
        self.assertEqual(session.start_at, started)
        self.assertEqual(session.opening_notes, "First opening")
        session.update_closing_control_state_session("Counted")
        self.assertEqual(session.state, "closing_control")
        self.assertEqual(
            session.update_closing_cash_details(12.50), {"successful": True}
        )
        session.action_pos_session_close()
        self.assertEqual(session.state, "closed")
        refusal = session.update_closing_cash_details(99)
        _logger.debug("Closed cashier session count refusal=%s", refusal)
        self.assertFalse(refusal["successful"])
        self.assertEqual(session.cash_register_balance_end_real, 12.50)
