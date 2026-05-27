from odoo.addons.pos_hr.tests.test_frontend import TestPosHrHttpCommon


class L10nPhPosTestBase(TestPosHrHttpCommon):
    """Shared base class for l10n_ph_pos tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.emp1.barcode = "APPROVER001"
        cls.emp2.barcode = "CASHIER002"

    def _open_main_session(self):
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        return self.main_pos_config.current_session_id
