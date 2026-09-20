from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestAccountAssetCommon


@tagged("post_install", "-at_install")
class TestResourceAssetLifecycle(TestAccountAssetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.loss_account = cls.company_data["default_account_expense"].copy()

    def _running_board(self, **vals):
        asset = self.create_asset(
            10000,
            "yearly",
            10,
            date_acquisition=self.today + relativedelta(years=-3),
            **vals,
        )
        asset.action_confirm()
        return asset

    def _dispose(self, asset, date=None):
        return (
            self.env["asset.modify"]
            .create(
                {
                    "asset_id": asset.id,
                    "modify_action": "dispose",
                    "loss_account_id": self.loss_account.id,
                    "date": date or self.today,
                }
            )
            .action_sell_dispose()
        )

    def test_confirming_a_board_puts_a_draft_asset_in_service(self):
        asset = self._running_board()
        self.assertEqual(asset.depreciation_state, "open")
        self.assertEqual(asset.state, "in_service")

    def test_confirming_a_board_leaves_an_asset_under_maintenance_alone(self):
        asset = self.create_asset(
            10000,
            "yearly",
            10,
            date_acquisition=self.today + relativedelta(years=-3),
            state="maintenance",
        )
        asset.action_confirm()
        self.assertEqual(asset.state, "maintenance")

    def test_pausing_and_resuming_a_board_leave_the_asset_in_service(self):
        asset = self._running_board()
        asset._pause(self.today)
        self.assertEqual(asset.depreciation_state, "paused")
        self.assertEqual(asset.state, "in_service")
        self.env["asset.modify"].with_context(resume_after_pause=True).create(
            {"asset_id": asset.id}
        ).action_modify()
        self.assertEqual(asset.depreciation_state, "open")
        self.assertEqual(asset.state, "in_service")

    def test_disposing_through_the_wizard_closes_the_board_and_disposes_the_asset(self):
        date = self.today + relativedelta(days=-1)
        asset = self._running_board()
        self._dispose(asset, date)
        self.assertRecordValues(
            asset,
            [
                {
                    "depreciation_state": "close",
                    "state": "disposed",
                    "date_disposal": date,
                    "active": False,
                }
            ],
        )

    def test_disposing_an_asset_with_a_running_board_opens_the_wizard(self):
        asset = self._running_board()
        action = asset.action_dispose()
        self.assertEqual(action["res_model"], "asset.modify")
        wizard = self.env["asset.modify"].browse(action["res_id"])
        self.assertEqual(wizard.asset_id, asset)
        self.assertEqual(wizard.modify_action, "dispose")
        self.assertEqual(asset.state, "in_service")
        self.assertTrue(asset.active)

    def test_disposing_several_assets_refuses_when_one_has_a_running_board(self):
        board = self._running_board()
        van = self.env["account.depreciation.board"].create(
            {"name": "Van", "kind_id": self.env.ref("resource_asset.kind_vehicle").id}
        )
        with self.assertRaises(UserError):
            (board + van).action_dispose()
        self.assertNotEqual(van.state, "disposed")

    def test_disposing_an_asset_without_a_running_board_disposes_it(self):
        van = self.env["account.depreciation.board"].create(
            {"name": "Van", "kind_id": self.env.ref("resource_asset.kind_vehicle").id}
        )
        draft = self.create_asset(1200, "yearly", 4)
        (van + draft).action_dispose()
        self.assertEqual((van + draft).mapped("state"), ["disposed", "disposed"])

    def test_disposing_an_asset_without_the_wizard_books_the_disposal(self):
        company = self.env.company
        company.gain_account_id = self.company_data["default_account_revenue"]
        company.loss_account_id = self.loss_account
        date = self.today + relativedelta(days=-2)
        asset = self._running_board()
        asset._dispose(date)
        self.assertRecordValues(
            asset,
            [
                {
                    "depreciation_state": "close",
                    "state": "disposed",
                    "date_disposal": date,
                    "active": False,
                }
            ],
        )
        self.assertEqual(
            asset.depreciation_move_ids._sorted_by_date()[-1].asset_move_type,
            "disposal",
        )

    def test_disposing_a_depreciating_asset_needs_the_gain_and_loss_accounts(self):
        company = self.env.company
        company.gain_account_id = False
        company.loss_account_id = False
        asset = self._running_board()
        with self.assertRaises(UserError):
            asset._dispose(self.today)
        self.assertEqual(asset.depreciation_state, "open")

    def test_disposing_an_asset_without_a_board_needs_no_accounts(self):
        van = self.env["account.depreciation.board"].create(
            {"name": "Van", "kind_id": self.env.ref("resource_asset.kind_vehicle").id}
        )
        van._dispose(self.today)
        self.assertRecordValues(
            van, [{"state": "disposed", "date_disposal": self.today, "active": False}]
        )

    def test_writing_disposed_on_a_running_board_is_refused(self):
        asset = self._running_board()
        with self.assertRaises(UserError):
            asset.write({"state": "disposed", "date_disposal": self.today})

    def test_cancelling_a_board_leaves_the_asset_state_alone(self):
        asset = self._running_board()
        asset.action_cancel()
        self.assertEqual(asset.depreciation_state, "cancelled")
        self.assertEqual(asset.state, "in_service")

    def test_restoring_a_disposed_asset_is_refused_while_its_board_is_closed(self):
        asset = self._running_board()
        self._dispose(asset)
        with self.assertRaises(UserError):
            asset.active = True

    def test_setting_a_closed_board_running_again_puts_the_asset_back_in_service(self):
        asset = self._running_board()
        self._dispose(asset)
        asset.action_reopen()
        self.assertRecordValues(
            asset,
            [
                {
                    "depreciation_state": "open",
                    "state": "in_service",
                    "date_disposal": False,
                    "active": True,
                }
            ],
        )
