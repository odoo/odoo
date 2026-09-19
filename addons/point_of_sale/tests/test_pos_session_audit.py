import logging
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import TestPoSCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPosSessionAudit(TestPoSCommon):
    """Exercise session invariants through the live ORM and PostgreSQL."""

    def setUp(self):
        super().setUp()
        self.config = self.basic_config

    def test_new_session_uses_replacement_journal_without_rewriting_history(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        session.action_pos_session_close()
        previous = session.cash_journal_id
        replacement = previous.copy({"name": "Replacement cash", "code": "RPLC"})

        self.cash_pm1.journal_id = replacement

        # _start_pos_session also rewrites config.payment_method_ids, which is a
        # separate historical reconfiguration path from opening a new register.
        self.config.open_ui()
        new_session = self.config.current_session_id
        _logger.debug(
            "Historical journal=%s new session journal=%s",
            session.cash_journal_id,
            new_session.cash_journal_id,
        )
        self.assertEqual(session.cash_journal_id, previous)
        self.assertEqual(new_session.cash_journal_id, replacement)

    def test_cash_journal_change_preserves_closed_session_cash_history(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        session.try_cash_in_out(
            "in", 10, "Historical float", self.env.user.partner_id.id, {}
        )
        session.cash_register_balance_end_real = 10
        session.action_pos_session_closing_control()
        report = self.env["report.point_of_sale.report_saledetails"]
        lines = {session.id: session.statement_line_ids}
        before = report._prepare_uncounted_cash_row(session, lines)
        previous_journal = session.cash_journal_id
        replacement = previous_journal.copy({"name": "New drawer", "code": "NEWC"})

        self.cash_pm1.journal_id = replacement

        after = report._prepare_uncounted_cash_row(session, lines)
        _logger.debug("Historical cash row before=%s after=%s", before, after)
        self.assertEqual(after, before)

    def test_cash_control_follows_payment_method_type(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        session.action_pos_session_close()
        self.assertTrue(session.cash_control)
        self.assertTrue(self.config.cash_control)
        previous_journal = session.cash_journal_id

        self.cash_pm1.journal_id = self.bank_pm1.journal_id

        _logger.debug(
            "Cash -> bank: method=%s config=%s session=%s journal=%s",
            self.cash_pm1.type,
            self.config.cash_control,
            session.cash_control,
            session.cash_journal_id,
        )
        self.assertFalse(self.config.cash_control)
        self.assertEqual(session.cash_journal_id, previous_journal)
        self.assertFalse(session.cash_control)

    def test_opening_date_can_be_unset(self):
        session = self._start_pos_session(self.cash_pm1, 0)

        session.start_at = False

        _logger.debug("Session %s has no opening date", session.id)
        self.assertFalse(session.start_at)

    def test_optional_opening_date_does_not_bypass_lock_dates(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        session.start_at = False
        lock_date = fields.Date.today() - timedelta(days=2)
        session.company_id.account_config_id.fiscalyear_lock_date = lock_date

        with self.assertRaises(ValidationError):
            session.start_at = fields.Datetime.to_datetime(lock_date)

        session.start_at = fields.Datetime.now()
        _logger.debug("Optional date still enforces fiscal lock %s", lock_date)

    def test_unrelated_activity_does_not_suppress_old_session_alert(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        session.start_at = fields.Datetime.now() - timedelta(days=8)
        session.activity_schedule("mail.mail_activity_data_todo")

        session._alert_old_sessions()
        session._alert_old_sessions()

        alerts = session.activity_ids.filtered(
            lambda activity: (
                activity.activity_type_id
                == self.env.ref("point_of_sale.mail_activity_old_session")
            )
        )
        _logger.debug("Old session activities: %s", session.activity_ids)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(len(session.activity_ids), 2)

    def test_reminders_exclude_recent_and_closed_sessions(self):
        closed = self._start_pos_session(self.cash_pm1, 0)
        closed.start_at = fields.Datetime.now() - timedelta(days=8)
        closed.action_pos_session_close()
        self.config.open_ui()
        recent = self.config.current_session_id
        recent.set_opening_control(0, "")

        recent._alert_old_sessions()

        self.assertFalse((closed | recent).activity_ids)
        recent.start_at = fields.Datetime.now() - timedelta(days=8)
        recent._alert_old_sessions()
        self.assertEqual(len(recent.activity_ids), 1)
        _logger.debug(
            "Reminder excludes recent/closed sessions, includes newly aged one"
        )

    def test_close_lock_refusal_restores_transaction_before_logging(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        self.env.flush_all()
        session.invalidate_recordset(["name"])
        execute = self.cr.execute

        def locked_execute(query, *args, **kwargs):
            if isinstance(query, str) and query.startswith(
                "SELECT id FROM pos_session"
            ):
                # A real PostgreSQL error aborts the transaction; a Python-only
                # mock of LockNotAvailable would hide the broken recovery path.
                return execute("DO $$ BEGIN RAISE lock_not_available; END $$")
            return execute(query, *args, **kwargs)

        with self.cr.savepoint():
            with patch.object(self.cr, "execute", locked_execute):
                try:
                    session._close_session()
                except UserError as error:
                    self.assertIn("Another user is currently closing", str(error))
                else:
                    self.fail("A locked session must refuse closing")
            # Do not let assertRaises' savepoint repair the transaction for us.
            self.cr.execute("SELECT 1")
            self.assertEqual(self.cr.fetchone(), (1,))
            _logger.debug("Close refusal left the transaction usable")

    def test_opening_balance_loads_only_latest_history_per_config(self):
        configs = self.config | self.config.copy({"name": "Second register"})
        self.config.payment_method_ids = self.cash_pm1
        (configs - self.config).payment_method_ids = self.cash_split_pm1
        history = self.env["pos.session"].create(
            [
                {
                    "config_id": config.id,
                    "name": f"History {config.id}/{index}",
                    "state": "closed",
                    "cash_register_balance_end_real": index + config.id,
                }
                for config in configs
                for index in range(20)
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        search = type(history).search
        fetch_query = type(history)._fetch_query
        materialized = []
        fetched_history = set()
        history_ids = set(history.ids)

        def measured_search(records, *args, **kwargs):
            result = search(records, *args, **kwargs)
            materialized.extend(result.ids)
            return result

        def measured_fetch(records, *args, **kwargs):
            result = fetch_query(records, *args, **kwargs)
            fetched_history.update(history_ids.intersection(result.ids))
            return result

        with (
            patch.object(type(history), "search", measured_search),
            patch.object(type(history), "_fetch_query", measured_fetch),
        ):
            sessions = self.env["pos.session"].create(
                [{"config_id": config.id} for config in configs]
            )

        _logger.debug(
            "Opening history: search returned %d sessions; fetched %d historical rows",
            len(materialized),
            len(fetched_history),
        )
        for session in sessions:
            self.assertEqual(
                session.cash_register_balance_start, 19 + session.config_id.id
            )
        self.assertLessEqual(len(materialized), len(configs))
        self.assertLessEqual(len(fetched_history), len(configs))

    def test_opening_history_preserves_rescue_and_empty_history_behavior(self):
        self.config.payment_method_ids = self.cash_pm1
        first = self.env["pos.session"].create({"config_id": self.config.id})
        self.assertEqual(first.cash_register_balance_start, 0)
        first.action_pos_session_close()
        rescue = self.env["pos.session"].create(
            {
                "config_id": self.config.id,
                "rescue": True,
                "cash_register_balance_end_real": 42,
            }
        )

        regular = self.env["pos.session"].create({"config_id": self.config.id})

        _logger.debug(
            "Opening chose latest rescue %s with cash=%s",
            rescue.id,
            regular.cash_register_balance_start,
        )
        self.assertEqual(regular.cash_register_balance_start, 42)

    def test_closing_summary_keeps_cash_bank_credit_and_unused_methods(self):
        session = self._start_pos_session(
            self.cash_pm1 | self.bank_pm1 | self.pay_later_pm | self.bank_split_pm1, 10
        )
        product = self.create_product("Summary product", self.categ_basic, 100, 50)
        self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(product, 1)],
                    "payments": [
                        (self.cash_pm1, 40),
                        (self.bank_pm1, 30),
                        (self.pay_later_pm, 30),
                    ],
                    "customer": self.customer,
                    "uuid": "session-summary-audit",
                }
            ]
        )
        session.try_cash_in_out("out", 5, "petty cash", self.env.user.partner_id.id, {})

        summary = session.get_closing_control_data()

        _logger.debug("Closing summary: %s", summary)
        self.assertEqual(summary["orders_details"], {"quantity": 1, "amount": 100})
        self.assertEqual(summary["default_cash_details"]["amount"], 45)
        self.assertEqual(summary["default_cash_details"]["payment_amount"], 40)
        methods = {
            method["id"]: method for method in summary["non_cash_payment_methods"]
        }
        for method, amount, count in [
            (self.bank_pm1, 30, 1),
            (self.pay_later_pm, 30, 1),
            (self.bank_split_pm1, 0, 0),
        ]:
            self.assertEqual(methods[method.id]["amount"], amount)
            self.assertEqual(methods[method.id]["number"], count)

    def test_closing_summary_without_cash(self):
        session = self._start_pos_session(self.bank_pm1, 0)

        summary = session.get_closing_control_data()

        # Extensions may add employee subtotals to this otherwise empty mapping.
        self.assertNotIn("id", summary["default_cash_details"])
        self.assertNotIn("amount", summary["default_cash_details"])
        self.assertEqual(len(summary["non_cash_payment_methods"]), 1)
        self.assertEqual(summary["non_cash_payment_methods"][0]["amount"], 0)

    def test_closing_summary_preserves_refunds_and_second_cash_method(self):
        methods = self.cash_pm1 | self.cash_split_pm1 | self.bank_pm1
        session = self._start_pos_session(methods, 10)
        product = self.create_product("Refund summary", self.categ_basic, 100, 50)
        self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(product, sign)],
                    "payments": [
                        (self.cash_pm1, 40 * sign),
                        (self.cash_split_pm1, 20 * sign),
                        (self.bank_pm1, 40 * sign),
                    ],
                    "customer": self.customer,
                    "uuid": f"summary-sign-{sign}",
                }
                for sign in (1, -1)
            ]
        )

        summary = session.get_closing_control_data()

        _logger.debug("Refund and second cash method summary: %s", summary)
        self.assertEqual(summary["orders_details"], {"quantity": 2, "amount": 0})
        self.assertEqual(summary["default_cash_details"]["id"], self.cash_pm1.id)
        self.assertEqual(summary["default_cash_details"]["amount"], 10)
        self.assertEqual(summary["default_cash_details"]["payment_amount"], 0)
        self.assertEqual(
            [
                (row["id"], row["amount"], row["number"])
                for row in summary["non_cash_payment_methods"]
            ],
            [
                (method.id, 0, 2)
                for method in session.payment_method_ids - self.cash_pm1
            ],
        )

    def test_duplicate_extension_models_are_loaded_once(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        payment_model = type(self.env["pos.payment"])
        load = payment_model._load_pos_data_search_read
        load_fields = payment_model._load_pos_data_fields
        with patch.object(
            type(session),
            "_get_model_names_to_load",
            return_value=["pos.order", "pos.payment", "pos.payment"],
        ):
            with patch.object(
                payment_model,
                "_load_pos_data_search_read",
                autospec=True,
                side_effect=load,
            ) as reads:
                data = session.load_data(["pos.order", "pos.payment"])
            with patch.object(
                payment_model,
                "_load_pos_data_fields",
                autospec=True,
                side_effect=load_fields,
            ) as field_reads:
                params = session.load_data_params()

        _logger.debug(
            "Duplicate model calls: data=%d fields=%d",
            reads.call_count,
            field_reads.call_count,
        )
        self.assertEqual(list(data), ["pos.session", "pos.order", "pos.payment"])
        self.assertEqual(list(params), ["pos.session", "pos.order", "pos.payment"])
        self.assertEqual(reads.call_count, 1)
        self.assertEqual(field_reads.call_count, 1)

    def test_real_account_move_loader_runs_once(self):
        session = self._start_pos_session(self.cash_pm1, 0)
        model_names = session._get_model_names_to_load(self.config)
        model = type(self.env["account.move"])
        load = model._load_pos_data_search_read
        with patch.object(
            model, "_load_pos_data_search_read", autospec=True, side_effect=load
        ) as reads:
            data = session.load_data(["account.move"])

        _logger.debug(
            "Actual extension chain: account.move declared=%d loaded=%d",
            model_names.count("account.move"),
            reads.call_count,
        )
        self.assertIn("account.move", data)
        self.assertEqual(reads.call_count, 1)
