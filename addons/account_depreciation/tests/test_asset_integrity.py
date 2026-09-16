from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account_depreciation.tests.common import TestAccountAssetCommon


@tagged("post_install", "-at_install")
class TestAssetIntegrity(TestAccountAssetCommon):
    def test_asset_group_must_belong_to_the_asset_company(self):
        other_company = self.env["res.company"].create({"name": "Other Co"})
        foreign_group = self.env["account.asset.group"].create(
            {"name": "foreign", "company_id": other_company.id}
        )
        with self.assertRaises(UserError):
            self.create_asset(
                value=1000,
                periodicity="yearly",
                periods=5,
                asset_group_id=foreign_group.id,
            )
            self.env.flush_all()

    def test_shared_asset_group_is_visible_to_every_company(self):
        shared = self.env["account.asset.group"].create(
            {"name": "shared", "company_id": False}
        )
        self.env.invalidate_all()
        visible = (
            self.env["account.asset.group"]
            .with_user(self.env.ref("base.user_admin"))
            .search([("id", "=", shared.id)])
        )
        self.assertEqual(visible, shared)

    def test_book_value_follows_the_state(self):
        self.env.company.gain_account_id = self.company_data[
            "default_account_revenue"
        ].copy()
        self.env.company.loss_account_id = self.company_data[
            "default_account_expense"
        ].copy()
        asset = self.create_asset(
            value=1000, periodicity="yearly", periods=5, value_salvage=200
        )
        asset.action_confirm()
        asset.depreciation_move_ids.filtered(lambda m: m.state != "posted")._post()
        asset._close(
            self.env["account.move.line"], date=fields.Date.to_date("2026-06-30")
        )
        asset.depreciation_move_ids.filtered(lambda m: m.state == "draft")._post()
        self.env.invalidate_all()
        self.assertEqual(asset.value_book, 0)

        asset.action_reopen()
        self.env.invalidate_all()
        self.assertEqual(
            asset.value_book,
            asset.value_depreciable_residual + asset.value_salvage,
            "value_book must be recomputed when the state changes",
        )

    def test_gross_increase_is_named_even_without_a_note(self):
        asset = self.create_asset(value=1000, periodicity="yearly", periods=5)
        asset.action_confirm()
        date = fields.Date.to_date("2022-06-30")
        self.env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "modify_action": "modify",
                "date": date,
                "value_depreciable_residual": asset._get_residual_value_at_date(date)
                + 500,
                "account_asset_counterpart_id": self.company_data[
                    "default_account_expense"
                ]
                .copy()
                .id,
            }
        ).action_modify()
        increase = asset.increase_ids
        self.assertTrue(increase.name, "a gross increase must carry a name")
        self.assertTrue(increase.display_name)

    def test_an_asset_cannot_be_created_running(self):
        with self.assertRaises(UserError):
            self.create_asset(
                value=1000, periodicity="yearly", periods=5, depreciation_state="open"
            )

    def test_bill_lines_must_share_one_posted_account(self):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2020-02-01",
                "line_ids": [
                    Command.create(
                        {
                            "name": "a",
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "debit": 100,
                        }
                    ),
                    Command.create(
                        {
                            "name": "b",
                            "account_id": self.company_data["default_account_assets"]
                            .copy()
                            .id,
                            "debit": 50,
                        }
                    ),
                    Command.create(
                        {
                            "name": "c",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "credit": 150,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        with self.assertRaises(ValidationError):
            self.create_asset(
                value=100,
                periodicity="yearly",
                periods=5,
                original_move_line_ids=[
                    Command.set(move.line_ids.filtered(lambda line: line.debit).ids)
                ],
            )

    def test_writing_an_unrelated_field_does_not_walk_the_board(self):
        asset = self.create_asset(value=6000, periodicity="monthly", periods=12)
        asset.action_confirm()
        self.assertTrue(asset.depreciation_move_ids)
        company_model = type(self.env["res.company"])
        original = company_model._get_user_fiscal_lock_date
        calls = []

        def counting(self, *args, **kwargs):
            calls.append(1)
            return original(self, *args, **kwargs)

        with patch.object(company_model, "_get_user_fiscal_lock_date", counting):
            asset.write({"name": "renamed"})
            self.env.flush_all()
        self.assertFalse(
            calls,
            "a write that cannot reach a depreciation entry must not read the lock date",
        )

    def test_changing_the_expense_account_rewrites_the_board_lines(self):
        asset = self.create_asset(value=1200, periodicity="yearly", periods=3)
        asset.action_confirm()
        new_expense = self.company_data["default_account_expense"].copy()
        asset.write({"account_depreciation_expense_id": new_expense.id})
        self.env.flush_all()
        posted_accounts = asset.depreciation_move_ids.line_ids.account_id
        self.assertIn(new_expense, posted_accounts)
        self.assertNotIn(self.company_data["default_account_expense"], posted_accounts)

    def test_disposal_moves_are_typed_not_inferred(self):
        self.env.company.gain_account_id = self.company_data[
            "default_account_revenue"
        ].copy()
        self.env.company.loss_account_id = self.company_data[
            "default_account_expense"
        ].copy()
        asset = self.create_asset(value=1000, periodicity="yearly", periods=5)
        asset.action_confirm()
        asset.depreciation_move_ids.filtered(lambda m: m.state != "posted")._post()
        asset._close(
            self.env["account.move.line"], date=fields.Date.to_date("2026-06-30")
        )
        disposal = asset.depreciation_move_ids.filtered(
            lambda m: m.asset_move_type == "disposal"
        )
        self.assertEqual(len(disposal), 1)
