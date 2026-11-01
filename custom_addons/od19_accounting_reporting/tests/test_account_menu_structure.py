from odoo.tests.common import TransactionCase


class TestAccountMenuStructure(TransactionCase):
    """Menu structure expectations for the Accounting app."""

    def _root_siblings(self, menu):
        return self.env["ir.ui.menu"].search(
            [("parent_id", "=", menu.parent_id.id), ("id", "!=", menu.id)]
        )

    def test_root_menu_renamed_to_accounting(self):
        menu = self.env.ref("account.menu_finance")
        self.assertEqual(menu.name, "Accounting")

    def test_inner_accounting_menu_renamed(self):
        menu = self.env.ref("account.menu_finance_entries")
        self.assertEqual(menu.name, "Accounting Entries")

    def test_settings_account_app_label_renamed(self):
        view = self.env.ref("account.res_config_settings_view_form")
        app = view._get_combined_arch().find(".//app[@name='account']")
        self.assertIsNotNone(app)
        self.assertEqual(app.get("string"), "Accounting")

    def test_finance_control_board_sits_before_reporting(self):
        board = self.env.ref(
            "od19_accounting_reporting.menu_od19_finance_control_dashboard"
        )
        review = self.env.ref("account.account_audit_menu")
        reporting = self.env.ref("account.menu_finance_reports")
        self.assertEqual(board.parent_id, reporting.parent_id)
        self.assertGreater(
            board.sequence,
            review.sequence,
            "Finance Control Board must come after the Review menu",
        )
        self.assertLess(
            board.sequence,
            reporting.sequence,
            "Finance Control Board must come before the Reporting menu",
        )

    def test_configuration_is_last_menu(self):
        configuration = self.env.ref("account.menu_finance_configuration")
        siblings = self._root_siblings(configuration)
        self.assertTrue(siblings)
        self.assertTrue(
            all(sibling.sequence <= configuration.sequence for sibling in siblings),
            "Configuration must be the last menu of the app",
        )
