# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_ph_pos.tests.common import L10nPhPosTestBase


@tagged("post_install_l10n", "post_install", "-at_install")
class TestLineVoidFlow(L10nPhPosTestBase):

    def _default_audit_payload(self, **overrides):
        payload = {
            "reason": "Wrong item selected",
            "passcode": "2580",
            "transaction_date": "2026-01-02 03:04:05",
            "cashier_employee_id": self.emp2.id,
            "product_id": self.product_a.id,
            "description": self.product_a.display_name,
            "quantity": 1,
            "unit_price": 25,
            "net_amount": 25,
        }
        payload.update(overrides)
        return payload

    def test_line_void_logging(self):
        session = self._open_main_session()

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(),
        )

        self.assertEqual(result["void_counter"], 1)
        self.assertIn("approver_name", result)
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertTrue(void_line)
        self.assertEqual(void_line.reason, "Wrong item selected")
        self.assertEqual(void_line.remark, "Line was voided.")
        self.assertEqual(
            fields.Datetime.to_string(void_line.transaction_date),
            "2026-01-02 03:04:05",
        )
        self.assertEqual(void_line.approver_employee_id, self.emp1)
        self.assertEqual(void_line.approver_badge_number, "APPROVER001")
        self.assertEqual(void_line.cashier_employee_id, self.emp2)
        self.assertEqual(void_line.cashier_badge_number, "CASHIER002")
        self.assertNotIn("approval_passcode", self.env["l10n_ph.pos.line.void"]._fields)
        self.assertNotIn("approval_role", self.env["l10n_ph.pos.line.void"]._fields)
        self.assertNotIn(
            "void_sequence_number",
            self.env["l10n_ph.pos.line.void"]._fields,
        )
        self.assertNotIn("details", self.env["l10n_ph.pos.line.void"]._fields)
        self.assertNotIn("employee_name", self.env["l10n_ph.pos.line.void"]._fields)
        self.assertNotIn(
            "cashier_employee_name",
            self.env["l10n_ph.pos.line.void"]._fields,
        )

        with self.assertRaises(AccessError):
            void_line.with_user(self.pos_admin).write({"reason": "Edited"})
        with self.assertRaises(AccessError):
            void_line.with_user(self.pos_admin).unlink()
        with self.assertRaises(AccessError):
            self.env["l10n_ph.pos.line.void"].with_user(self.pos_admin).create(
                {
                    "approver_employee_id": self.emp1.id,
                    "config_id": session.config_id.id,
                    "session_id": session.id,
                    "product_id": self.product_a.id,
                },
            )

    def test_quantity_decrease_logging(self):
        session = self._open_main_session()

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            {
                "action_type": "quantity_decrease",
                "reason": "Customer changed mind",
                "passcode": "2580",
                "transaction_date": "2026-02-03 04:05:06",
                "product_id": self.product_a.id,
                "description": self.product_a.display_name,
                "quantity": 1,
                "old_quantity": 2,
                "new_quantity": 1,
                "unit_price": 25,
                "net_amount": 25,
            },
        )

        self.assertEqual(result["action_type"], "quantity_decrease")
        self.assertEqual(result["void_counter"], 0)
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertEqual(void_line.remark, "Quantity reduced from 2 to 1.")

    def test_quantity_decrease_without_quantities_uses_generic_remark(self):
        session = self._open_main_session()

        session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(
                action_type="quantity_decrease",
                old_quantity=None,
                new_quantity=None,
            ),
        )
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertEqual(void_line.remark, "Quantity was reduced.")

    @mute_logger("odoo.addons.l10n_ph_pos.models.pos_session")
    def test_invalid_transaction_date_falls_back_to_now(self):
        session = self._open_main_session()
        before = fields.Datetime.now()

        session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(transaction_date="not-a-date"),
        )

        after = fields.Datetime.now()
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertGreaterEqual(
            void_line.transaction_date,
            before - timedelta(seconds=1),
        )
        self.assertLessEqual(void_line.transaction_date, after + timedelta(seconds=1))

    def test_timezone_aware_transaction_date_is_normalized_to_utc(self):
        session = self._open_main_session()

        session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(transaction_date="2026-01-02T03:04:05+08:00"),
        )

        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertEqual(
            fields.Datetime.to_string(void_line.transaction_date),
            "2026-01-01 19:04:05",
        )

    def test_zulu_transaction_date_is_normalized_to_utc(self):
        session = self._open_main_session()

        session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(transaction_date="2026-01-02T03:04:05Z"),
        )

        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertEqual(
            fields.Datetime.to_string(void_line.transaction_date),
            "2026-01-02 03:04:05",
        )

    def test_line_void_defaults_action_type(self):
        session = self._open_main_session()

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(action_type=False),
        )
        self.assertEqual(result["action_type"], "line_void")

    def test_line_void_action_uid_is_idempotent(self):
        session = self._open_main_session()
        payload = self._default_audit_payload(action_uid="offline-void-uid-1")

        first = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(payload)
        second = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            payload,
        )

        self.assertEqual(first["void_counter"], 1)
        self.assertEqual(second["void_counter"], 1)
        self.assertIn("approver_name", second)
        logs = self.env["l10n_ph.pos.line.void"].search(
            [("source_uid", "=", "offline-void-uid-1")],
        )
        self.assertEqual(len(logs), 1)

    def test_line_void_approver_id_bypasses_passcode_lookup(self):
        session = self._open_main_session()

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(passcode="", approver_id=self.emp1.id),
        )

        self.assertEqual(result["void_counter"], 1)
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)], limit=1,
        )
        self.assertEqual(void_line.approver_employee_id, self.emp1)

    def test_line_void_invalid_approver_id_rejected(self):
        session = self._open_main_session()

        with self.assertRaises(UserError):
            session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                self._default_audit_payload(passcode="", approver_id=self.emp4.id),
            )

    def test_cashier_falls_back_to_session_employee_when_not_in_payload(self):
        session = self._open_main_session()

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(
                cashier_employee_id=False,
                cashier_user_id=False,
            ),
        )

        self.assertEqual(result["void_counter"], 1)
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)], limit=1,
        )
        self.assertTrue(void_line.cashier_employee_id)

    def test_pending_audit_action_failure_stays_in_pending(self):
        """A pending action that fails to replay is kept in l10n_ph_pending_audit_actions."""
        session = self._open_main_session()
        bad_action = {
            "action_uid": "fail-replay-1",
            "action_type": "line_void",
            "reason": "Will fail",
            "transaction_date": "2026-03-01 00:00:00",
            "cashier_employee_id": self.emp2.id,
            "product_id": False,
            "description": "Bad product",
            "quantity": 1,
            "unit_price": 0,
            "net_amount": 0,
            "approver_id": self.emp1.id,
        }
        good_action = {
            "action_uid": "good-replay-1",
            "action_type": "line_void",
            "reason": "Will succeed",
            "transaction_date": "2026-03-01 00:00:00",
            "cashier_employee_id": self.emp2.id,
            "product_id": self.product_a.id,
            "description": self.product_a.display_name,
            "quantity": 1,
            "unit_price": 25,
            "net_amount": 25,
            "approver_id": self.emp1.id,
        }
        order = self.env["pos.order"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.main_pos_config.id,
                "session_id": session.id,
                "pricelist_id": self.main_pos_config.pricelist_id.id,
                "amount_paid": 0.0,
                "amount_total": 0.0,
                "amount_tax": 0.0,
                "amount_return": 0.0,
                "to_invoice": False,
                "l10n_ph_pending_audit_actions": [bad_action, good_action],
            },
        )

        with mute_logger("odoo.addons.l10n_ph_pos.models.pos_order"):
            order._l10n_ph_process_pending_audit_actions()

        self.assertEqual(len(order.l10n_ph_pending_audit_actions), 1)
        self.assertEqual(
            order.l10n_ph_pending_audit_actions[0]["action_uid"], "fail-replay-1",
        )
        log = self.env["l10n_ph.pos.line.void"].search(
            [("source_uid", "=", "good-replay-1")], limit=1,
        )
        self.assertTrue(log)

    def test_pending_audit_actions_are_processed_from_order_sync(self):
        session = self._open_main_session()
        order = self.env["pos.order"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.main_pos_config.id,
                "session_id": session.id,
                "partner_id": self.partner_a.id,
                "pricelist_id": self.main_pos_config.pricelist_id.id,
                "amount_paid": 0.0,
                "amount_total": 0.0,
                "amount_tax": 0.0,
                "amount_return": 0.0,
                "to_invoice": False,
                "l10n_ph_pending_audit_actions": [
                    {
                        "action_uid": "offline-sync-audit-1",
                        "action_type": "line_void",
                        "reason": "Offline replay",
                        "transaction_date": "2026-03-01 10:11:12",
                        "cashier_employee_id": self.emp2.id,
                        "product_id": self.product_a.id,
                        "description": self.product_a.display_name,
                        "quantity": 1,
                        "old_quantity": 1,
                        "new_quantity": 0,
                        "unit_price": 25,
                        "net_amount": 25,
                        "approver_id": self.emp1.id,
                    },
                ],
            },
        )

        order._l10n_ph_process_pending_audit_actions()
        log = self.env["l10n_ph.pos.line.void"].search(
            [("source_uid", "=", "offline-sync-audit-1")],
            limit=1,
        )

        self.assertTrue(log)
        self.assertEqual(log.reason, "Offline replay")
        self.assertEqual(log.cashier_employee_id, self.emp2)
        self.assertEqual(order.session_id.config_id.l10n_ph_void_counter, 1)
        self.assertFalse(order.l10n_ph_pending_audit_actions)

    def test_line_void_self_approval_logs_with_cashier_as_approver(self):
        session = self._open_main_session()
        self.emp2.l10n_ph_pos_allow_self_line_void = True

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(passcode="", cashier_employee_id=self.emp2.id),
        )

        self.assertEqual(result["void_counter"], 1)
        self.assertIn("approver_name", result)
        void_log = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertTrue(void_log)
        self.assertEqual(void_log.approver_employee_id, self.emp2)
        self.assertEqual(void_log.cashier_employee_id, self.emp2)

    def test_allow_self_line_void_flag_is_available_for_pos_cashiers(self):
        self.emp3.l10n_ph_pos_allow_self_line_void = True
        self.main_pos_config.basic_employee_ids.l10n_ph_pos_allow_self_line_void = True

        users = self.main_pos_config.basic_employee_ids.user_id
        payload = self.env["res.users"]._load_pos_data_read(users, self.main_pos_config)

        self.assertTrue(payload)
        for user_data in payload:
            self.assertIn("_l10n_ph_pos_allow_self_line_void", user_data)
            self.assertTrue(user_data["_l10n_ph_pos_allow_self_line_void"])

    def test_allow_self_line_void_resolves_cashier_from_user_id(self):
        session = self._open_main_session()
        self.pos_admin.employee_id.l10n_ph_pos_allow_self_line_void = True

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(
                passcode="",
                cashier_employee_id=False,
                cashier_user_id=self.pos_admin.id,
            ),
        )

        self.assertEqual(result["approver_name"], self.pos_admin.employee_id.name)
        void_log = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertTrue(void_log)
        self.assertEqual(void_log.approver_employee_id, self.pos_admin.employee_id)

    def test_pos_user_payload_includes_allow_self_line_void_flag(self):
        self.emp1.l10n_ph_pos_allow_self_line_void = True

        payload = self.env["res.users"]._load_pos_data_read(
            self.pos_admin,
            self.main_pos_config,
        )

        self.assertEqual(len(payload), 1)
        self.assertIn("_l10n_ph_pos_allow_self_line_void", payload[0])
        self.assertEqual(
            payload[0]["_l10n_ph_pos_allow_self_line_void"],
            bool(self.pos_admin.employee_id.l10n_ph_pos_allow_self_line_void),
        )
        self.assertIn("_l10n_ph_cashier_employee_id", payload[0])
        self.assertEqual(
            payload[0]["_l10n_ph_cashier_employee_id"],
            self.pos_admin.employee_id.id,
        )

    def test_unsupported_action_is_rejected(self):
        session = self._open_main_session()

        with self.assertRaises(UserError):
            session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                self._default_audit_payload(action_type="price_override"),
            )

    def test_missing_passcode_is_rejected(self):
        session = self._open_main_session()

        with self.assertRaises(UserError):
            session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                self._default_audit_payload(passcode=""),
            )

    def test_missing_product_is_rejected(self):
        session = self._open_main_session()

        with self.assertRaises(UserError):
            session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                self._default_audit_payload(product_id=False),
            )

    def test_line_void_invalid_passcode(self):
        session = self._open_main_session()

        with self.assertRaises(UserError):
            session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                {
                    "reason": "Wrong item selected",
                    "passcode": "0000",
                },
            )

    def test_line_void_rejects_duplicate_matching_passcodes(self):
        session = self._open_main_session()
        self.emp2.pin = self.emp1.pin

        with self.assertRaisesRegex(UserError, "multiple employees"):
            session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                self._default_audit_payload(passcode=self.emp1.pin),
            )

    def test_accumulated_total_sales_updates_when_order_is_paid(self):
        session = self._open_main_session()
        order = self.env["pos.order"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.main_pos_config.id,
                "session_id": session.id,
                "partner_id": self.partner_a.id,
                "lines": [
                    Command.create(
                        {
                            "name": self.product_a.display_name,
                            "product_id": self.product_a.id,
                            "price_unit": 100,
                            "discount": 0,
                            "qty": 1,
                            "tax_ids": [Command.clear()],
                            "price_subtotal": 100,
                            "price_subtotal_incl": 100,
                        },
                    ),
                ],
                "pricelist_id": self.main_pos_config.pricelist_id.id,
                "amount_paid": 100.0,
                "amount_total": 100.0,
                "amount_tax": 0.0,
                "amount_return": 0.0,
                "to_invoice": False,
            },
        )

        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 0.0)
        order.action_pos_order_paid()
        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 100.0)
        order.action_pos_order_paid()
        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 100.0)

    def test_settings_show_existing_accumulated_total_sales(self):
        self.main_pos_config.l10n_ph_accumulated_total_sales = 321.5

        settings = self.env["res.config.settings"].create(
            {"pos_config_id": self.main_pos_config.id},
        )

        self.assertEqual(settings.l10n_ph_accumulated_total_sales, 321.5)
        self.assertEqual(
            self.main_pos_config.l10n_ph_accumulated_total_sales,
            321.5,
        )

    def test_accumulated_total_sales_updates_when_order_is_synced_from_ui(self):
        session = self._open_main_session()

        ui_order = {
            "amount_paid": 100.0,
            "amount_return": 0.0,
            "amount_tax": 0.0,
            "amount_total": 100.0,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "fiscal_position_id": False,
            "pricelist_id": self.main_pos_config.pricelist_id.id,
            "name": "Order 98765-123-0001",
            "lines": [
                (
                    0,
                    0,
                    {
                        "id": 42,
                        "name": self.product_a.display_name,
                        "product_id": self.product_a.id,
                        "price_unit": 100.0,
                        "discount": 0.0,
                        "qty": 1,
                        "tax_ids": [[6, False, []]],
                        "price_subtotal": 100.0,
                        "price_subtotal_incl": 100.0,
                    },
                ),
            ],
            "session_id": session.id,
            "payment_ids": [
                (
                    0,
                    0,
                    {
                        "amount": 100.0,
                        "name": fields.Datetime.now(),
                        "payment_method_id": session.payment_method_ids[:1].id,
                    },
                ),
            ],
            "uuid": "98765-123-0001",
            "user_id": self.env.uid,
            "to_invoice": False,
        }

        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 0.0)
        self.env["pos.order"].sync_from_ui([ui_order])
        synced_order = self.env["pos.order"].search(
            [("uuid", "=", "98765-123-0001")],
            limit=1,
        )
        self.assertEqual(synced_order.state, "paid")
        self.assertTrue(synced_order.l10n_ph_accumulated_counted)
        self.assertEqual(synced_order.config_id, self.main_pos_config)
        self.assertEqual(self.main_pos_config.l10n_ph_accumulated_total_sales, 100.0)
