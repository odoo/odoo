# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_ph_pos.tests.common import L10nPhPosTestBase


@tagged("post_install_l10n", "post_install", "-at_install")
class TestLineVoidExport(L10nPhPosTestBase):

    def _create_log(
        self, session, reason, passcode="2580", transaction_date="2026-01-02 03:04:05",
    ):
        session.with_user(self.pos_admin).l10n_ph_log_order_line_action(
            {
                "reason": reason,
                "passcode": passcode,
                "transaction_date": transaction_date,
                "cashier_employee_id": self.emp2.id,
                "product_id": self.product_a.id,
                "description": self.product_a.display_name,
                "quantity": 1,
                "unit_price": 25,
                "net_amount": 25,
            },
        )

    def test_export_csv_requires_pos_manager(self):
        session = self._open_main_session()
        self._create_log(session, "Export ACL")

        self.authenticate("pos_user", "pos_user")
        with mute_logger("odoo.http"):
            response = self.url_open("/l10n_ph_pos/line_voids/export.csv")
        self.assertEqual(response.status_code, 403)

    def test_export_csv_success_headers_and_sanitization(self):
        session = self._open_main_session()
        self._create_log(session, "=2+5")

        self.authenticate("pos_admin", "pos_admin")
        response = self.url_open("/l10n_ph_pos/line_voids/export.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers.get("Content-Type", ""))
        self.assertIn(
            "line_void_transactions.csv",
            response.headers.get("Content-Disposition", ""),
        )

        csv_body = response.text
        self.assertIn("Transaction Date & Timestamp", csv_body)
        self.assertIn("Approver RFID / Badge #", csv_body)
        self.assertIn("Cashier RFID / Badge #", csv_body)
        self.assertIn("APPROVER001", csv_body)
        self.assertIn("CASHIER002", csv_body)
        self.assertIn("'=2+5", csv_body)

    def test_export_csv_sanitizes_injection_chars(self):
        session = self._open_main_session()
        for prefix in ("=cmd", "+cmd", "@cmd", "-non-numeric"):
            self._create_log(session, prefix)

        self.authenticate("pos_admin", "pos_admin")
        csv_body = self.url_open("/l10n_ph_pos/line_voids/export.csv").text
        for prefix in ("=cmd", "+cmd", "@cmd", "-non-numeric"):
            self.assertIn(f"'{prefix}", csv_body)

    def test_export_csv_employee_filter(self):
        session = self._open_main_session()
        self._create_log(session, "Employee 1 filter", passcode="2580")
        self._create_log(session, "Employee 2 filter", passcode="5651")

        self.authenticate("pos_admin", "pos_admin")
        response = self.url_open(
            f"/l10n_ph_pos/line_voids/export.csv?employee_id={self.emp1.id}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Employee 1 filter", response.text)
        self.assertNotIn("Employee 2 filter", response.text)

    def test_export_csv_config_filter(self):
        session = self._open_main_session()
        self._create_log(session, "Config filter test")

        self.authenticate("pos_admin", "pos_admin")
        response = self.url_open(
            f"/l10n_ph_pos/line_voids/export.csv?config_id={self.main_pos_config.id}",
        )
        self.assertIn("Config filter test", response.text)
        response_wrong = self.url_open(
            "/l10n_ph_pos/line_voids/export.csv?config_id=999999",
        )
        self.assertNotIn("Config filter test", response_wrong.text)

    def test_export_csv_date_range_filter(self):
        session = self._open_main_session()
        self._create_log(
            session, "Before range", transaction_date="2026-01-01 00:00:00",
        )
        self._create_log(session, "In range", transaction_date="2026-06-15 12:00:00")
        self._create_log(session, "After range", transaction_date="2026-12-31 23:59:59")

        self.authenticate("pos_admin", "pos_admin")
        response = self.url_open(
            "/l10n_ph_pos/line_voids/export.csv?from_date=2026-06-01&to_date=2026-06-30",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("In range", response.text)
        self.assertNotIn("Before range", response.text)
        self.assertNotIn("After range", response.text)

    def test_export_csv_rejects_invalid_parameters(self):
        session = self._open_main_session()
        self._create_log(session, "Bad request checks")

        self.authenticate("pos_admin", "pos_admin")
        with mute_logger("odoo.http"):
            invalid_int = self.url_open(
                "/l10n_ph_pos/line_voids/export.csv?config_id=abc",
            )
            invalid_range = self.url_open(
                "/l10n_ph_pos/line_voids/export.csv?from_date=2026-01-03&to_date=2026-01-02",
            )
            invalid_limit = self.url_open(
                "/l10n_ph_pos/line_voids/export.csv?limit=999999",
            )
        self.assertEqual(invalid_int.status_code, 400)
        self.assertEqual(invalid_range.status_code, 400)
        self.assertEqual(invalid_limit.status_code, 400)
