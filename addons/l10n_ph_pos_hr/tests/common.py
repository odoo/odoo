from odoo.addons.pos_hr.tests.test_frontend import TestPosHrHttpCommon


class L10nPhPosTestBase(TestPosHrHttpCommon):
    """Shared base class for l10n_ph_pos_hr tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.emp1.barcode = "APPROVER001"
        cls.emp2.barcode = "CASHIER002"

    def _open_main_session(self):
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        return self.main_pos_config.current_session_id

    def _default_audit_payload(self, **overrides):
        """Return a valid l10n_ph_log_order_line_action payload, approved by emp1
        (passcode 2580) for a line voided by emp2, ready for per-test overrides."""
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
