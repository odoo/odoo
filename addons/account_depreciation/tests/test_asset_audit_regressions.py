import datetime
import inspect
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import TestAccountAssetCommon


@tagged("post_install", "-at_install")
class TestAssetAuditRegressions(TestAccountAssetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.gain_account = cls.company_data["default_account_expense"].copy(
            {"code": "799950", "name": "Audit gain"}
        )
        cls.loss_account = cls.company_data["default_account_expense"].copy(
            {"code": "699950", "name": "Audit loss"}
        )
        cls.company.gain_account_id = cls.gain_account
        cls.company.loss_account_id = cls.loss_account

    def _running_asset(self, **kwargs):
        asset = self.create_asset(1200, "yearly", 4, **kwargs)
        asset.action_confirm()
        return asset

    def _disposal_move(self, asset):
        asset._close(self.env["account.move.line"], date=datetime.date(2026, 6, 30))
        return asset.depreciation_move_ids.filtered(
            lambda move: move.asset_move_type == "disposal"
        )

    def test_depreciation_value_inverse_on_a_plain_entry(self):
        asset = self.create_asset(1200, "yearly", 4)
        asset._create_depreciation_entries()
        move = asset.depreciation_move_ids.sorted(lambda m: (m.date, m.id))[0]
        self.assertEqual(move.state, "draft")
        self.assertEqual(len(move.line_ids), 2)

        move.depreciation_value = 111.0

        self.assertEqual(sorted(move.line_ids.mapped("balance")), [-111.0, 111.0])
        self.assertEqual(
            move.line_ids.filtered(
                lambda line: line.account_id == asset.account_depreciation_expense_id
            ).balance,
            111.0,
        )

    def test_depreciation_value_inverse_refuses_a_disposal_entry(self):
        asset = self._running_asset()
        disposal = self._disposal_move(asset)
        self.assertGreater(len(disposal.line_ids), 2)

        with self.assertRaisesRegex(UserError, "not a plain two-line depreciation"):
            disposal.depreciation_value = 999.0

    def test_asset_depreciation_line_ignores_the_gain_loss_line(self):
        asset = self._running_asset()
        disposal = self._disposal_move(asset)
        self.assertIn(
            self.loss_account,
            disposal.line_ids.account_id,
            "the disposal entry should carry a gain/loss line for this fixture",
        )

        self.assertNotIn(
            self.loss_account,
            disposal._get_asset_depreciation_line().account_id,
        )

    def test_disposal_depreciation_value_uses_the_accumulated_account(self):
        asset = self._running_asset()
        disposal = self._disposal_move(asset)
        accumulated = disposal.line_ids.filtered(
            lambda line: line.account_id == asset.account_depreciation_id
        )
        self.assertEqual(len(accumulated), 1)

        self.assertAlmostEqual(
            disposal.depreciation_value,
            asset.value_original - asset.value_salvage - abs(accumulated.balance),
        )

    def test_revaluation_down_keeps_the_caller_reference(self):
        asset = self._running_asset()
        wizard = self.env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "date": "2021-06-30",
                "modify_action": "modify",
                "name": "cut",
            }
        )
        self.assertGreater(wizard.value_depreciable_residual, 0)
        wizard.write(
            {
                "value_depreciable_residual": wizard.value_depreciable_residual / 2,
                "value_salvage": 0.0,
            }
        )
        wizard.action_modify()

        decrease = asset.depreciation_move_ids.filtered(
            lambda move: move.asset_move_type == "negative_revaluation"
        )
        self.assertTrue(decrease)
        self.assertIn("Value decrease for", decrease.ref)

    def test_board_computation_rejects_an_unknown_method(self):
        asset = self.create_asset(1200, "yearly", 4)
        self.env.cr.execute(
            "UPDATE account_depreciation_board SET depreciation_method = 'exotic' WHERE id = %s",
            (asset.id,),
        )
        asset.invalidate_recordset(["depreciation_method"])

        with self.assertRaisesRegex(UserError, "no board computation"):
            asset._get_board_amount(
                1000.0,
                datetime.date(2024, 1, 1),
                datetime.date(2024, 12, 31),
                1800,
                1000.0,
                datetime.date(2024, 1, 1),
            )

    def test_invoicing_user_can_create_an_asset_with_an_original_value(self):
        user = self.env["res.users"].create(
            {
                "name": "Invoicing only",
                "login": "asset_invoicing_only",
                "company_id": self.company.id,
                "company_ids": [Command.set(self.company.ids)],
                "group_ids": [
                    Command.link(self.env.ref("account.group_account_invoice").id),
                    Command.link(self.env.ref("base.group_user").id),
                ],
            }
        )
        asset = (
            self.env["account.depreciation.board"]
            .with_user(user)
            .create(
                {
                    "name": "created by invoicing",
                    "account_depreciation_id": self.company_data[
                        "default_account_assets"
                    ].id,
                    "account_depreciation_expense_id": self.company_data[
                        "default_account_expense"
                    ].id,
                    "depreciation_journal_id": self.company_data[
                        "default_journal_misc"
                    ].id,
                    "value_original": 500.0,
                    "date_acquisition": "2024-01-01",
                }
            )
        )
        self.assertEqual(asset.value_original, 500.0)
        with self.assertRaises(AccessError):
            asset.with_user(user).write({"value_original": 600.0})

    def test_turn_as_asset_does_not_need_active_ids(self):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2024-01-01",
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "d",
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "balance": 100.0,
                        }
                    ),
                    Command.create(
                        {
                            "name": "c",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "balance": -100.0,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        line = move.line_ids.filtered(
            lambda l: l.account_id == self.company_data["default_account_assets"]
        )

        action = line.turn_as_asset()

        self.assertEqual(
            action["context"]["default_original_move_line_ids"],
            [Command.set(line.ids)],
        )

    def test_non_deductible_tax_value_follows_the_amount(self):
        tax_account = self.company_data["default_account_tax_purchase"]
        tax = self.env["account.tax"].create(
            {
                "name": "20% half non deductible",
                "amount_type": "percent",
                "amount": 20.0,
                "type_tax_use": "purchase",
                "country_id": self.company.account_config_id.account_fiscal_country_id.id,
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "factor_percent": 50.0,
                            "account_id": tax_account.id,
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "factor_percent": 50.0,
                            "account_id": tax_account.id,
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "factor_percent": 50.0,
                            "account_id": tax_account.id,
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "factor_percent": 50.0,
                            "account_id": tax_account.id,
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
            }
        )
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2024-01-01",
                "date": "2024-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "car",
                            "quantity": 1,
                            "price_unit": 1000.0,
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "tax_ids": [Command.set(tax.ids)],
                        }
                    )
                ],
            }
        )
        line = bill.invoice_line_ids
        self.assertAlmostEqual(line.non_deductible_tax_value, 100.0)

        line.price_unit = 2000.0

        self.assertAlmostEqual(
            line.non_deductible_tax_value,
            200.0,
            msg="the tax value must follow the amount it is derived from",
        )

    def test_board_values_accumulate_chronologically_whatever_the_cached_order(self):
        asset = self._running_asset()
        board = asset.depreciation_move_ids._sorted_by_date()
        self.assertEqual(board.mapped("date"), sorted(board.mapped("date")))
        remaining = board.mapped("asset_remaining_value")
        self.assertEqual(remaining, sorted(remaining, reverse=True))
        cached = [(move.id, move.asset_remaining_value) for move in board]
        self.env.invalidate_all()
        self.assertEqual(
            [(move.id, move.asset_remaining_value) for move in board], cached
        )

    def test_report_groups_are_ordered_by_name(self):
        report = self.env.ref("account_depreciation.assets_report")
        groups = [
            self.env["account.asset.group"].create({"name": name})
            for name in ("Zulu", "Alpha", "Mike")
        ]
        for index, group in enumerate(groups):
            self.create_asset(
                (index + 1) * 100, "yearly", 4, asset_group_id=group.id
            ).action_confirm()
        self.create_asset(500, "yearly", 4).action_confirm()

        options = report.get_options(
            {
                "assets_grouping_field": "asset_group_id",
                "unfold_all": True,
                "date": {
                    "date_from": "2020-01-01",
                    "date_to": "2027-12-31",
                    "filter": "custom",
                    "mode": "range",
                },
            }
        )
        names = [
            line["name"]
            for line in report._get_lines(options)
            if line["level"] == 1 and not line["name"].startswith("Total")
        ]

        self.assertEqual(names, ["Alpha", "Mike", "Zulu", "(No Asset Group)"])

    def test_fixed_asset_account_shows_on_an_asset_without_bills(self):
        plain = self.env["res.users"].create(
            {
                "name": "Plain accountant",
                "login": "asset_plain_accountant",
                "company_id": self.company.id,
                "company_ids": [Command.set(self.company.ids)],
                "group_ids": [
                    Command.link(self.env.ref("account.group_account_user").id),
                    Command.link(self.env.ref("base.group_user").id),
                ],
            }
        )
        asset = self.create_asset(1200, "yearly", 4)

        self.assertTrue(asset.with_user(plain).display_account_asset_id)

    def test_sibling_assets_stay_visible_when_computed_together(self):
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
                            "debit": 300,
                        }
                    ),
                    Command.create(
                        {
                            "name": "b",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "credit": 300,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        line = move.line_ids.filtered(lambda aml: aml.debit)
        siblings = self.env["account.depreciation.board"]
        for index in range(3):
            siblings |= self.create_asset(
                300,
                "yearly",
                4,
                name=f"sibling {index}",
                original_move_line_ids=[Command.set(line.ids)],
            )

        Asset = self.env["account.depreciation.board"]
        siblings.invalidate_recordset()
        one_at_a_time = [
            len(Asset.browse(asset.id).linked_assets_ids) for asset in siblings
        ]
        siblings.invalidate_recordset()
        as_a_batch = [len(asset.linked_assets_ids) for asset in siblings]

        self.assertEqual(one_at_a_time, [2, 2, 2])
        self.assertEqual(
            as_a_batch,
            one_at_a_time,
            "linked_assets_ids must not depend on how many records share the compute",
        )
        siblings[0].action_confirm()
        siblings.invalidate_recordset()
        self.assertTrue(siblings[1].warning_count_assets)

    def test_board_asks_each_fiscal_year_once_for_the_whole_batch(self):
        assets = self.env["account.depreciation.board"]
        for index in range(5):
            assets |= self.create_asset(
                6000, "monthly", 24, name=f"batched {index}", depreciation_state="draft"
            )
        company_model = type(self.env["res.company"])
        original = company_model.compute_fiscalyear_dates
        seen = []

        def counting(self, current_date):
            seen.append((self.id, current_date))
            return original(self, current_date)

        with patch.object(company_model, "compute_fiscalyear_dates", counting):
            assets._create_depreciation_entries()

        self.assertTrue(seen)
        self.assertEqual(
            len(seen),
            len(set(seen)),
            "the board must not ask the same company for the same date twice",
        )
        self.assertFalse(
            self.env.cr.cache.get("account_depreciation.fiscalyear_dates"),
            "the memo must not outlive the computation that opened it",
        )

    def test_default_journal_is_searched_once_per_company(self):
        AccountJournal = type(self.env["account.journal"])
        original = AccountJournal.search
        calls = []

        def counting(self, *args, **kwargs):
            calls.append(1)
            return original(self, *args, **kwargs)

        with patch.object(AccountJournal, "search", counting):
            assets = self.env["account.depreciation.board"].create(
                [
                    {
                        "name": f"journal batch {index}",
                        "account_depreciation_id": self.company_data[
                            "default_account_assets"
                        ].id,
                        "account_depreciation_expense_id": self.company_data[
                            "default_account_expense"
                        ].id,
                        "value_original": 1000,
                        "date_acquisition": "2020-02-01",
                        "depreciation_prorata": "none",
                    }
                    for index in range(10)
                ]
            )
            assets.mapped("depreciation_journal_id")

        self.assertEqual(len(assets.depreciation_journal_id), 1)
        self.assertEqual(
            len(calls), 1, "one company needs one default-journal lookup, not ten"
        )

    def test_an_explicit_journal_survives_a_forced_recompute(self):
        other_journal = self.company_data["default_journal_misc"].copy(
            {"name": "Second misc", "code": "MSC2"}
        )
        asset = self.create_asset(
            1200, "yearly", 4, depreciation_journal_id=other_journal.id
        )
        self.env.flush_all()

        self.env.add_to_compute(asset._fields["depreciation_journal_id"], asset)
        self.env.flush_all()

        self.assertEqual(
            asset.depreciation_journal_id,
            other_journal,
            "a journal that already matches the company must not be reset",
        )

    def test_writing_value_residual_on_an_asset_does_nothing(self):
        asset = self.create_asset(1000, "yearly", 4)
        field = asset._fields["value_depreciable_residual"]
        self.assertFalse(field.store)
        self.assertIsNone(field.inverse)

        written = self.create_asset(
            1000, "yearly", 4, value_depreciable_residual=999999.0
        )
        self.assertEqual(
            written.value_depreciable_residual,
            1000.0,
            "create() drops the key outright -- it reaches neither column nor cache",
        )

        asset.write({"value_depreciable_residual": 123456.0})
        self.env.flush_all()
        asset.invalidate_recordset()
        self.assertEqual(asset.value_depreciable_residual, 1000.0)

    def test_gross_increase_value_comes_from_the_original_value(self):
        asset = self._running_asset()
        wizard = self.env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "date": datetime.date(2021, 6, 30),
                "account_asset_counterpart_id": self.company_data[
                    "default_account_revenue"
                ].id,
            }
        )
        wizard.value_depreciable_residual += 400
        wizard.value_salvage += 100
        wizard.action_modify()

        increase = asset.increase_ids
        self.assertEqual(len(increase), 1)
        self.assertEqual(increase.value_original, 500)
        self.assertEqual(increase.value_salvage, 100)
        self.assertEqual(
            increase.value_depreciable,
            400,
            "the amount to depreciate is original - salvage, not a written residual",
        )
        self.assertEqual(increase.currency_id, asset.currency_id)

    def test_save_as_profile_produces_a_profile_matching_the_asset(self):
        asset = self._running_asset(
            depreciation_method="degressive",
            depreciation_factor=0.25,
            depreciation_duration=7,
            depreciation_period="1",
        )
        action = asset.action_save_profile()

        profile = self.env["account.depreciation.profile"].browse(action["res_id"])
        self.assertEqual(asset.depreciation_profile_id, profile)
        for fname, value in profile._get_asset_defaults().items():
            self.assertEqual(
                asset[fname].id if asset._fields[fname].relational else asset[fname],
                value,
                f"the saved profile lost {fname}",
            )

    def test_a_closed_gross_increase_is_not_re_credited_with_the_sale(self):
        asset = self.create_asset(4000, "yearly", 3)
        asset.action_confirm()
        wizard = self.env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "date": datetime.date(2020, 12, 31),
                "account_asset_counterpart_id": self.company_data[
                    "default_account_revenue"
                ].id,
            }
        )
        wizard.value_depreciable_residual += 600
        wizard.action_modify()
        increase = asset.increase_ids
        self.assertEqual(len(increase), 1)
        self.assertEqual(increase.value_depreciable_residual, 0.0)

        self.env["asset.modify"].create(
            {
                "asset_id": increase.id,
                "date": datetime.date(2026, 6, 30),
                "modify_action": "pause",
            }
        ).action_pause()
        self.assertEqual(increase.depreciation_state, "paused")

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2026-06-30",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "sale",
                            "price_unit": 1500,
                            "quantity": 1,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        revenue_account = invoice.invoice_line_ids.account_id

        asset._close(
            invoice.invoice_line_ids, date=datetime.date(2026, 6, 30), message="sold"
        )
        self.env.flush_all()

        sale_moves = (asset | increase).depreciation_move_ids.filtered(
            lambda move: move.asset_move_type == "sale"
        )
        self.assertEqual(
            len(sale_moves), 1, "only the asset that was sold gets a sale entry"
        )
        self.assertEqual(sale_moves.depreciation_board_id, asset)
        neutralised = sum(
            line.balance
            for line in sale_moves.line_ids
            if line.account_id == revenue_account
        )
        self.assertEqual(
            neutralised,
            1500.0,
            "the invoice revenue must be neutralised once, not once per closed asset",
        )
        gain = sum(
            line.balance
            for line in sale_moves.line_ids
            if line.account_id == self.gain_account
        )
        self.assertEqual(gain, -1500.0, "the gain must not be doubled")
        self.assertTrue(
            increase.depreciation_move_ids.filtered(
                lambda move: move.asset_move_type == "disposal"
            ),
            "the increase is still closed, by a disposal entry",
        )

    def test_confirming_runs_the_board_inside_a_savepoint(self):
        asset = self.create_asset(1000, "yearly", 4)
        asset.account_depreciation_id = False
        source = inspect.getsource(type(asset).action_confirm)

        self.assertIn(
            "self.env.cr.savepoint()",
            source,
            "action_confirm() must contain the CheckViolation it catches",
        )
        self.assertLess(
            source.index("self.env.cr.savepoint()"),
            source.index("psycopg.errors.CheckViolation"),
            "the savepoint has to open before the block that can raise",
        )
        with self.assertRaises(ValidationError):
            asset.action_confirm()

    def test_open_asset_on_several_records_does_not_ask_for_a_singleton(self):
        assets = self.create_asset(1000, "yearly", 4) | self.create_asset(
            2000, "yearly", 4
        )

        action = assets.open_board(["form"])

        self.assertFalse(action["res_id"])
        self.assertEqual(sorted(action["domain"][0][2]), sorted(assets.ids))

    def test_residual_before_the_board_starts_is_not_zero(self):
        asset = self.create_asset(10000, "yearly", 5, import_depreciation=4000)
        asset.action_confirm()
        first_beginning = min(
            asset.depreciation_move_ids.mapped("asset_depreciation_beginning_date")
        )
        self.assertGreater(
            first_beginning,
            datetime.date(2021, 1, 1),
            "the import must have swallowed the first entries for this to test anything",
        )

        residual = asset._get_residual_value_at_date(datetime.date(2020, 12, 31))

        self.assertEqual(
            residual,
            10000 - 4000,
            "before any entry begins the asset still carries original - salvage - imported",
        )
        wizard = self.env["asset.modify"].create(
            {"asset_id": asset.id, "date": datetime.date(2020, 12, 31)}
        )
        self.assertEqual(wizard.value_depreciable_residual, 6000.0)

    def test_residual_of_a_negative_asset_stays_negative_before_the_board(self):
        asset = self.create_asset(-10000, "yearly", 5, import_depreciation=-4000)
        asset.action_confirm()

        self.assertEqual(
            asset._get_residual_value_at_date(datetime.date(2020, 12, 31)), -6000
        )

    def _modify_wizard(self, asset, action, **kwargs):
        return self.env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "modify_action": action,
                "date": datetime.date(2021, 6, 30),
                **kwargs,
            }
        )

    def test_informational_text_names_the_gain_account_when_selling_above_book(self):
        asset = self._running_asset()
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2021-06-30",
                "invoice_line_ids": [
                    Command.create(
                        {"name": "s", "price_unit": 9000, "quantity": 1, "tax_ids": []}
                    )
                ],
            }
        )
        invoice.action_post()
        wizard = self._modify_wizard(
            asset,
            "sell",
            invoice_ids=[Command.set(invoice.ids)],
            invoice_line_ids=[Command.set(invoice.invoice_line_ids.ids)],
        )

        self.assertEqual(wizard.gain_or_loss, "gain")
        self.assertIn(self.gain_account.display_name, wizard.informational_text)
        self.assertNotIn(self.loss_account.display_name, wizard.informational_text)

    def test_informational_text_names_the_loss_account_when_disposing(self):
        asset = self._running_asset()
        wizard = self._modify_wizard(asset, "dispose")

        self.assertEqual(wizard.gain_or_loss, "loss")
        self.assertIn(self.loss_account.display_name, wizard.informational_text)
        self.assertNotIn(self.gain_account.display_name, wizard.informational_text)

    def test_informational_text_names_no_account_when_there_is_no_outcome(self):
        asset = self._running_asset()
        wizard = self._modify_wizard(asset, "modify")

        self.assertEqual(wizard.gain_or_loss, "no")
        self.assertNotIn(self.gain_account.display_name, wizard.informational_text)
        self.assertNotIn(self.loss_account.display_name, wizard.informational_text)

    def test_informational_text_covers_every_action(self):
        asset = self._running_asset()
        for action in ("dispose", "sell", "pause", "modify"):
            wizard = self._modify_wizard(asset, action)
            self.assertTrue(
                wizard.informational_text, f"{action} produced no informational text"
            )
        resume = self.env["asset.modify"].create(
            {"asset_id": asset.id, "date": datetime.date(2021, 6, 30)}
        )
        self.assertTrue(resume.informational_text, "the resume branch produced none")

    def test_informational_text_announces_a_gross_increase_only_when_there_is_one(self):
        asset = self._running_asset()
        plain = self._modify_wizard(asset, "modify")
        self.assertFalse(plain.gain_value)
        self.assertFalse(plain._get_value_increase_text())
        self.assertNotIn("value increase", plain.informational_text.lower())

        increasing = self._modify_wizard(asset, "modify")
        increasing.value_depreciable_residual += 500
        self.assertTrue(increasing.gain_value)
        self.assertIn("value increase", increasing.informational_text.lower())

    def _bill_with_assets(self, count, label):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2020-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": f"{label} line",
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "price_unit": 900,
                            "quantity": 1,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        bill.action_post()
        line = bill.line_ids.filtered(
            lambda aml: aml.account_id == self.company_data["default_account_assets"]
        )
        assets = self.env["account.depreciation.board"]
        for index in range(count):
            assets |= self.create_asset(
                900,
                "yearly",
                5,
                name=f"{label} {index}",
                original_move_line_ids=[Command.set(line.ids)],
            )
        self.env.flush_all()
        return bill, assets

    def test_deleting_the_last_asset_untypes_the_bill(self):
        bill, assets = self._bill_with_assets(1, "single")
        self.assertEqual(bill.asset_move_type, "purchase")

        assets.unlink()
        self.env.flush_all()

        self.assertFalse(bill.asset_move_type)

    def test_deleting_every_asset_of_a_bill_untypes_it_too(self):
        bill, assets = self._bill_with_assets(2, "pair")
        self.assertEqual(len(bill.capitalised_board_ids), 2)

        assets.unlink()
        self.env.flush_all()

        self.assertFalse(bill.capitalised_board_ids)
        self.assertFalse(bill.asset_move_type)

    def test_deleting_one_of_two_assets_leaves_the_bill_typed(self):
        bill, assets = self._bill_with_assets(2, "keep")

        assets[0].unlink()
        self.env.flush_all()

        self.assertEqual(len(bill.capitalised_board_ids), 1)
        self.assertEqual(bill.asset_move_type, "purchase")

    def test_deleting_assets_logs_one_note_per_bill(self):
        bill, assets = self._bill_with_assets(2, "chatter")
        before = len(bill.message_ids)

        assets.unlink()
        self.env.flush_all()

        notes = bill.message_ids[: len(bill.message_ids) - before]
        self.assertEqual(
            len(notes), 1, "both deletions are batched into a single note per move"
        )
        self.assertIn("has been deleted", notes.body)
