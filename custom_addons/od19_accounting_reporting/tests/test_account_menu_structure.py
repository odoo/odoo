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

    def test_finance_control_board_is_first_menu(self):
        board = self.env.ref(
            "od19_accounting_reporting.menu_od19_finance_control_dashboard"
        )
        dashboard = self.env.ref("account.menu_board_journal_1")
        self.assertEqual(board.parent_id, dashboard.parent_id)
        self.assertLess(
            board.sequence,
            dashboard.sequence,
            "Finance Control Board must open the app, before the core Dashboard",
        )
        siblings = self._root_siblings(board)
        self.assertTrue(siblings)
        self.assertTrue(
            all(board.sequence < sibling.sequence for sibling in siblings),
            "Finance Control Board must be the first menu of the app",
        )

    def test_configuration_is_last_menu(self):
        configuration = self.env.ref("account.menu_finance_configuration")
        siblings = self._root_siblings(configuration)
        self.assertTrue(siblings)
        self.assertTrue(
            all(sibling.sequence <= configuration.sequence for sibling in siblings),
            "Configuration must be the last menu of the app",
        )
