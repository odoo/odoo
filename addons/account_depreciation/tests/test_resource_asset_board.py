import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .common import TestAccountAssetCommon


@tagged("post_install", "-at_install")
class TestResourceAssetBoard(TestAccountAssetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vehicle = cls.env.ref("resource_asset.kind_vehicle")

    def _plain_asset(self, **vals):
        return self.env["resource.asset"].create(
            {"name": "Delivery van", "kind_id": self.vehicle.id, **vals}
        )

    def test_an_asset_without_a_board_keeps_its_own_dates(self):
        van = self._plain_asset(
            date_acquisition=datetime.date(2019, 5, 1),
            date_disposal=datetime.date(2024, 5, 1),
            state="disposed",
        )
        self.assertFalse(van.depreciation_state)
        self.assertEqual(van.date_acquisition, datetime.date(2019, 5, 1))
        self.assertEqual(van.date_disposal, datetime.date(2024, 5, 1))
        self.assertFalse(van.board_id)
        van.active = False
        self.assertFalse(van.active)

    def test_a_board_takes_the_fallback_kind_when_nothing_gives_one(self):
        asset = self.create_asset(1200, "yearly", 4)
        self.assertEqual(asset.depreciation_state, "draft")
        self.assertEqual(
            asset.kind_id, self.env.ref("account_depreciation.kind_fixed_asset")
        )

    def test_a_board_takes_its_profile_kind(self):
        profile = self.env["account.depreciation.profile"].create(
            {
                "name": "Vans",
                "kind_id": self.vehicle.id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
            }
        )
        asset = self.create_asset(1200, "yearly", 4, depreciation_profile_id=profile.id)
        self.assertEqual(asset.kind_id, self.vehicle)

    def test_the_accounting_action_lists_boards_only(self):
        van = self._plain_asset()
        board = self.create_asset(1200, "yearly", 4)
        action = self.env.ref("account_depreciation.action_account_asset_form")
        listed = self.env["account.depreciation.board"].search(eval(action.domain))  # noqa: S307  a literal domain from our own data file
        self.assertIn(board, listed)
        self.assertNotIn(van, listed.asset_id)

    def test_copying_a_plain_asset_does_not_make_it_a_board(self):
        van = self._plain_asset()
        self.assertFalse(van.copy().depreciation_state)

    def test_an_employee_reads_the_asset_but_not_its_valuation(self):
        board = self.create_asset(1200, "yearly", 4)
        employee = new_test_user(
            self.env, login="asset_board_employee", groups="base.group_user"
        )
        self.assertEqual(board.with_user(employee).name, board.name)
        with self.assertRaises(AccessError):
            board.with_user(employee).read(["value_book"])

    def test_an_asset_user_without_accounting_rights_creates_an_asset(self):
        asset_user = new_test_user(
            self.env,
            login="asset_board_asset_user",
            groups="base.group_user,resource_asset.group_asset_user",
        )
        van = (
            self.env["resource.asset"]
            .with_user(asset_user)
            .create(
                {
                    "name": "Delivery van",
                    "kind_id": self.env.ref("account_depreciation.kind_fixed_asset").id,
                }
            )
        )
        self.assertFalse(van.sudo().depreciation_state)

    def test_a_gross_increase_is_a_component_and_an_increase_of_its_parent(self):
        today = fields.Date.today()
        asset = self.create_asset(
            10000,
            "yearly",
            10,
            date_acquisition=today + relativedelta(years=-6, months=-6),
            value_salvage=2500,
        )
        asset.action_confirm()
        self.env["asset.modify"].create(
            {
                "name": "Engine overhaul",
                "asset_id": asset.id,
                "value_depreciable_residual": asset.value_depreciable_residual + 1000,
                "value_salvage": asset.value_salvage + 500,
                "date": today + relativedelta(months=-6, days=-1),
                "account_asset_counterpart_id": self.company_data[
                    "default_account_revenue"
                ].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
            }
        ).action_modify()
        increase = asset.increase_ids
        self.assertEqual(len(increase), 1)
        self.assertEqual(increase.increased_board_id, asset)
        self.assertEqual(increase.parent_id, asset.asset_id)
        self.assertIn(increase.asset_id, asset.child_ids)
        self.assertEqual(asset.count_increase, 1)
