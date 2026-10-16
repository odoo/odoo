# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_ph_pos_hr.tests.common import L10nPhPosTestBase


@tagged("post_install_l10n", "post_install", "-at_install")
class TestLineVoidFlow(L10nPhPosTestBase):

    # -- Audit logging --------------------------------------------------

    def test_line_void_logging(self):
        session = self._open_main_session()

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(),
        )

        self.assertEqual(result["void_counter"], 1)
        self.assertEqual(result["approver_name"], self.emp1.name)
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertRecordValues(void_line, [{
            "reason": "Wrong item selected",
            "remark": "Line was voided.",
            "approver_employee_id": self.emp1.id,
            "approver_badge_number": "APPROVER001",
            "cashier_employee_id": self.emp2.id,
            "cashier_badge_number": "CASHIER002",
        }])
        self.assertEqual(
            fields.Datetime.to_string(void_line.transaction_date),
            "2026-01-02 03:04:05",
        )

    def test_line_void_log_is_immutable(self):
        """The audit log can only be created via l10n_ph_log_order_line_action;
        direct ORM create/write/unlink are blocked for everyone but sudo."""
        session = self._open_main_session()
        session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(),
        )
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
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
        """Quantity decreases are logged without incrementing the void counter."""
        session = self._open_main_session()

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(
                action_type="quantity_decrease",
                old_quantity=2,
                new_quantity=1,
            ),
        )

        self.assertEqual(result, {
            "void_counter": 0,
            "approver_name": self.emp1.name,
            "action_type": "quantity_decrease",
        })
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertEqual(void_line.remark, "Quantity reduced from 2 to 1.")

    def test_quantity_decrease_remark_without_quantities_is_generic(self):
        session = self._open_main_session()
        for old_quantity, new_quantity in ((None, None), (2, None), (None, 1)):
            with self.subTest(old_quantity=old_quantity, new_quantity=new_quantity):
                session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                    self._default_audit_payload(
                        action_type="quantity_decrease",
                        old_quantity=old_quantity,
                        new_quantity=new_quantity,
                    ),
                )
                void_line = self.env["l10n_ph.pos.line.void"].search(
                    [("session_id", "=", session.id)],
                    order="id desc",
                    limit=1,
                )
                self.assertEqual(void_line.remark, "Quantity was reduced.")

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
        logs = self.env["l10n_ph.pos.line.void"].search(
            [("source_uid", "=", "offline-void-uid-1")],
        )
        self.assertEqual(len(logs), 1)

    # -- Transaction date parsing -----------------------------------------

    def test_transaction_date_normalization(self):
        cases = [
            ("2026-01-02 03:04:05", "2026-01-02 03:04:05"),
            ("2026-01-02T03:04:05+08:00", "2026-01-01 19:04:05"),
            ("2026-01-02T03:04:05Z", "2026-01-02 03:04:05"),
        ]
        session = self._open_main_session()
        for transaction_date, expected in cases:
            with self.subTest(transaction_date=transaction_date):
                session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                    self._default_audit_payload(transaction_date=transaction_date),
                )
                void_line = self.env["l10n_ph.pos.line.void"].search(
                    [("session_id", "=", session.id)],
                    order="id desc",
                    limit=1,
                )
                self.assertEqual(
                    fields.Datetime.to_string(void_line.transaction_date),
                    expected,
                )

    @mute_logger("odoo.addons.l10n_ph_pos_hr.models.pos_session")
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

    # -- Approver & passcode resolution -----------------------------------

    def test_l10n_ph_log_order_line_action_rejects_invalid_payloads(self):
        session = self._open_main_session()
        cases = [
            ("unsupported action type", {"action_type": "price_override"}, "Unsupported audit action"),
            ("missing passcode and approver", {"passcode": "", "approver_id": False}, "passcode or approver is required"),
            ("missing product", {"product_id": False}, "product is required"),
            ("passcode matches no employee", {"passcode": "0000"}, "Invalid passcode"),
            ("approver_id without matching passcode", {"passcode": "", "approver_id": self.emp1.id}, "Invalid passcode"),
            ("approver_id not authorized", {"passcode": "", "approver_id": self.emp4.id}, "not allowed for this action"),
        ]
        for label, overrides, message in cases:
            with self.subTest(label), self.assertRaisesRegex(UserError, message):
                session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                    self._default_audit_payload(**overrides),
                )

    def test_l10n_ph_log_order_line_action_rejects_duplicate_pin_matches(self):
        session = self._open_main_session()
        self.emp2.pin = self.emp1.pin

        with self.assertRaisesRegex(UserError, "multiple employees"):
            session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                self._default_audit_payload(passcode=self.emp1.pin),
            )

    def test_line_void_approver_id_with_correct_passcode(self):
        session = self._open_main_session()

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(approver_id=self.emp1.id),
        )

        self.assertEqual(result["void_counter"], 1)
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertEqual(void_line.approver_employee_id, self.emp1)

    # -- Cashier resolution & self-approval bypass -------------------------

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
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertTrue(void_line.cashier_employee_id)

    def test_missing_cashier_raises_user_error(self):
        """If neither the payload nor the session can resolve a cashier employee,
        logging the action must fail loudly instead of silently picking one."""
        userless = new_test_user(
            self.env, login="pos_no_employee", groups="point_of_sale.group_pos_user",
        )
        session = self.env["pos.session"].create(
            {"config_id": self.main_pos_config.id, "user_id": userless.id},
        )

        with self.assertRaisesRegex(UserError, "Could not determine the cashier"):
            session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
                self._default_audit_payload(
                    cashier_employee_id=False,
                    cashier_user_id=False,
                ),
            )

    def test_line_void_self_approval_logs_with_cashier_as_approver(self):
        session = self._open_main_session()
        self.emp2.l10n_ph_pos_allow_self_line_void = True

        result = session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(passcode="", cashier_employee_id=self.emp2.id),
        )

        self.assertEqual(result["void_counter"], 1)
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertRecordValues(void_line, [{
            "approver_employee_id": self.emp2.id,
            "cashier_employee_id": self.emp2.id,
        }])

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
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )
        self.assertEqual(void_line.approver_employee_id, self.pos_admin.employee_id)

    def test_load_pos_data_read_includes_allow_self_line_void_flag(self):
        """`_load_pos_data_read` must expose each user's self-approval flag and
        linked cashier employee, sourced from their own employee record."""
        self.admin.l10n_ph_pos_allow_self_line_void = True

        payload = self.env["res.users"]._load_pos_data_read(
            self.pos_admin + self.emp1.user_id,
            self.main_pos_config,
        )

        payload_by_id = {data["id"]: data for data in payload}
        self.assertEqual(
            payload_by_id[self.pos_admin.id]["_l10n_ph_pos_allow_self_line_void"],
            True,
        )
        self.assertEqual(
            payload_by_id[self.pos_admin.id]["_l10n_ph_cashier_employee_id"],
            self.admin.id,
        )
        self.assertEqual(
            payload_by_id[self.emp1.user_id.id]["_l10n_ph_pos_allow_self_line_void"],
            False,
        )

    # -- Offline / pending action replay -----------------------------------

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

        with mute_logger("odoo.addons.l10n_ph_pos_hr.models.pos_order"):
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

        self.assertRecordValues(log, [{
            "reason": "Offline replay",
            "cashier_employee_id": self.emp2.id,
        }])
        self.assertEqual(order.session_id.config_id.l10n_ph_void_counter, 1)
        self.assertFalse(order.l10n_ph_pending_audit_actions)

    # -- Access control & multi-company isolation ---------------------------

    def test_line_void_log_not_readable_by_plain_pos_user(self):
        """Only POS managers may read the audit log: the backend list view
        (and its standard export) is manager-only, so the model ACL must be too."""
        session = self._open_main_session()
        session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(),
        )
        void_line = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )

        with self.assertRaises(AccessError):
            void_line.with_user(self.pos_user).read(["reason"])

    def test_line_void_log_is_scoped_by_company(self):
        """The multi-company ir.rule must hide void logs of another company."""
        session = self._open_main_session()
        session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            self._default_audit_payload(),
        )
        own_log = self.env["l10n_ph.pos.line.void"].search(
            [("session_id", "=", session.id)],
            limit=1,
        )

        company_2 = self.setup_other_company()["company"]
        employee_2 = self.env["hr.employee"].create(
            {"name": "Other Company Employee", "company_id": company_2.id},
        )
        config_2 = self.env["pos.config"].with_company(company_2).create(
            {"name": "Other Company POS", "company_id": company_2.id},
        )
        session_2 = self.env["pos.session"].create({"config_id": config_2.id})
        other_log = self.env["l10n_ph.pos.line.void"].sudo().create(
            {
                "approver_employee_id": employee_2.id,
                "config_id": config_2.id,
                "session_id": session_2.id,
                "product_id": self.product_a.id,
            },
        )

        visible_logs = self.env["l10n_ph.pos.line.void"].with_user(
            self.pos_admin,
        ).search([])
        self.assertIn(own_log, visible_logs)
        self.assertNotIn(other_log, visible_logs)
