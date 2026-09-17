from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, freeze_time, tagged

from odoo.addons.account.tests.common_report_engine import TestAccountReportsCommon


@freeze_time("2021-07-01")
@tagged("post_install", "-at_install")
class TestAccountAsset(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        today = fields.Date.today()
        cls.truck = cls.env["resource.asset"].create(
            {
                "account_asset_id": cls.company_data["default_account_assets"].id,
                "account_depreciation_id": cls.company_data["default_account_assets"]
                .copy()
                .id,
                "account_depreciation_expense_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": cls.company_data["default_journal_misc"].id,
                "name": "truck",
                "date_acquisition": today + relativedelta(years=-6, months=-6),
                "value_original": 10000,
                "value_salvage": 2500,
                "depreciation_duration": 10,
                "depreciation_period": "12",
                "depreciation_method": "linear",
            }
        )
        cls.truck.action_confirm()
        moves_to_post = cls.env["account.move"].search(
            [
                ("state", "=", "draft"),
                ("auto_post", "!=", "no"),
                ("checked", "=", True),
            ]
        )
        moves_to_post._post()

        cls.account_asset_model_fixedassets = cls.env[
            "account.depreciation.profile"
        ].create(
            {
                "account_depreciation_id": cls.company_data["default_account_assets"]
                .copy()
                .id,
                "account_depreciation_expense_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "account_asset_id": cls.company_data["default_account_assets"].id,
                "depreciation_journal_id": cls.company_data[
                    "default_journal_purchase"
                ].id,
                "name": "Hardware - 3 Years",
                "depreciation_duration": 3,
                "depreciation_period": "12",
            }
        )

        cls.closing_invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_line_ids": [(0, 0, {"price_unit": 100})],
            }
        )

        cls.env.company.loss_account_id = cls.company_data[
            "default_account_expense"
        ].copy()
        cls.env.company.gain_account_id = cls.company_data[
            "default_account_revenue"
        ].copy()
        cls.assert_counterpart_account_id = (
            cls.company_data["default_account_expense"].copy().id
        )

        cls.env.user.group_ids += cls.env.ref("analytic.group_analytic_accounting")
        analytic_plan = cls.env["account.analytic.plan"].create(
            {
                "name": "Default Plan",
            }
        )
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Test Account",
                "plan_id": analytic_plan.id,
            }
        )

    def update_form_values(self, asset_form):
        for i in range(len(asset_form.depreciation_move_ids)):
            with asset_form.depreciation_move_ids.edit(i) as line_edit:
                line_edit.asset_remaining_value

    def test_account_asset_no_tax(self):
        self.account_asset_model_fixedassets.account_depreciation_expense_id.tax_ids = (
            self.tax_purchase_a
        )
        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 2000.0,
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "CEO's Car",
                "value_original": 12000.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
            }
        )
        CEO_car._onchange_depreciation_profile_id()
        CEO_car.depreciation_prorata = "constant_periods"
        CEO_car.depreciation_duration = 5

        CEO_car.action_confirm()

        self.assertFalse(
            any(CEO_car.depreciation_move_ids.line_ids.mapped("tax_line_id"))
        )

    def test_00_account_asset(self):
        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 2000.0,
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "CEO's Car",
                "value_original": 12000.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
            }
        )
        CEO_car._onchange_depreciation_profile_id()
        CEO_car.depreciation_prorata = "constant_periods"
        CEO_car.depreciation_duration = 5

        CEO_car.action_confirm()

        CEO_car.flush_recordset()

        self.assertEqual(
            CEO_car.depreciation_state, "open", "Asset should be in Open state"
        )

        self.assertEqual(
            CEO_car.depreciation_duration + 1,
            len(CEO_car.depreciation_move_ids),
            "Depreciation lines not created correctly",
        )

        self.assertTrue(
            all(CEO_car.depreciation_move_ids.mapped(lambda m: m.auto_post != "no"))
        )
        with self.assertRaises(UserError):
            CEO_car.depreciation_move_ids.action_post()

        CEO_car.depreciation_move_ids.write({"auto_post": "no"})
        CEO_car.depreciation_move_ids.action_post()
        self.assertEqual(
            CEO_car.depreciation_state, "open", "State of asset should be runing"
        )
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 2000,
                    "value_depreciable_residual": 0,
                    "value_salvage": 2000,
                }
            ],
        )

        self.assertRecordValues(
            CEO_car.depreciation_move_ids.sorted(lambda l: l.date),
            [
                {
                    "amount_total": 1000,
                    "asset_remaining_value": 9000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 7000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 5000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 3000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 1000,
                },
                {
                    "amount_total": 1000,
                    "asset_remaining_value": 0,
                },
            ],
        )

        CEO_car.depreciation_move_ids._reverse_moves(cancel=True)
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 12000,
                    "value_depreciable_residual": 10000,
                    "value_salvage": 2000,
                }
            ],
        )
        reversed_moves_values = [
            {
                "amount_total": 1000,
                "asset_remaining_value": 11000,
                "state": "posted",
            },
            {
                "amount_total": 2000,
                "asset_remaining_value": 13000,
                "state": "posted",
            },
            {
                "amount_total": 2000,
                "asset_remaining_value": 15000,
                "state": "posted",
            },
            {
                "amount_total": 2000,
                "asset_remaining_value": 17000,
                "state": "posted",
            },
            {
                "amount_total": 2000,
                "asset_remaining_value": 19000,
                "state": "posted",
            },
            {
                "amount_total": 1000,
                "asset_remaining_value": 20000,
                "state": "posted",
            },
            {
                "amount_total": 1000,
                "asset_remaining_value": 19000,
                "state": "posted",
            },
            {
                "amount_total": 2000,
                "asset_remaining_value": 17000,
                "state": "posted",
            },
            {
                "amount_total": 2000,
                "asset_remaining_value": 15000,
                "state": "posted",
            },
            {
                "amount_total": 2000,
                "asset_remaining_value": 13000,
                "state": "posted",
            },
            {
                "amount_total": 2000,
                "asset_remaining_value": 11000,
                "state": "posted",
            },
            {
                "amount_total": 1000,
                "asset_remaining_value": 10000,
                "state": "posted",
            },
            {
                "amount_total": 10000,
                "asset_remaining_value": 0,
                "state": "draft",
            },
        ]

        self.assertRecordValues(
            CEO_car.depreciation_move_ids.sorted(lambda l: l.date),
            reversed_moves_values,
        )
        self.assertRecordValues(
            CEO_car.depreciation_move_ids.filtered(
                lambda l: l.state == "draft"
            ).line_ids,
            [
                {
                    "debit": 0,
                    "credit": 10000,
                    "account_id": CEO_car.account_depreciation_id.id,
                },
                {
                    "debit": 10000,
                    "credit": 0,
                    "account_id": CEO_car.account_depreciation_expense_id.id,
                },
            ],
        )

        CEO_car._close(
            self.closing_invoice.invoice_line_ids,
            date=fields.Date.today() + relativedelta(days=-1),
        )
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 12000,
                    "value_depreciable_residual": 10000,
                    "value_salvage": 2000,
                }
            ],
        )
        self.assertRecordValues(
            CEO_car.depreciation_move_ids.sorted(lambda l: (l.date, l.id)),
            [
                {
                    "amount_total": 12000,
                    "asset_remaining_value": 0,
                    "state": "draft",
                },
                {
                    "amount_total": 1000,
                    "asset_remaining_value": 1000,
                    "state": "posted",
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 3000,
                    "state": "posted",
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 5000,
                    "state": "posted",
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 7000,
                    "state": "posted",
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 9000,
                    "state": "posted",
                },
                {
                    "amount_total": 1000,
                    "asset_remaining_value": 10000,
                    "state": "posted",
                },
                {
                    "amount_total": 1000,
                    "asset_remaining_value": 9000,
                    "state": "posted",
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 7000,
                    "state": "posted",
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 5000,
                    "state": "posted",
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 3000,
                    "state": "posted",
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 1000,
                    "state": "posted",
                },
                {
                    "amount_total": 1000,
                    "asset_remaining_value": 0,
                    "state": "posted",
                },
            ],
        )
        closing_move = CEO_car.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )
        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "debit": 0,
                    "credit": 12000,
                    "account_id": CEO_car.account_asset_id.id,
                },
                {
                    "debit": 0,
                    "credit": 0,
                    "account_id": CEO_car.account_depreciation_id.id,
                },
                {
                    "debit": 100,
                    "credit": 0,
                    "account_id": self.closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "debit": 11900,
                    "credit": 0,
                    "account_id": self.env.company.loss_account_id.id,
                },
            ],
        )
        closing_move.action_post()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 0,
                    "value_depreciable_residual": 0,
                    "value_salvage": 2000,
                }
            ],
        )

    def test_00_account_asset_new(self):
        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 2000.0,
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "CEO's Car",
                "value_original": 12000.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
            }
        )
        CEO_car._onchange_depreciation_profile_id()
        CEO_car.depreciation_prorata = "constant_periods"
        CEO_car.depreciation_duration = 5

        CEO_car.action_confirm()

        CEO_car.depreciation_move_ids.write({"auto_post": "no"})
        CEO_car.depreciation_move_ids.action_post()
        self.assertEqual(
            CEO_car.depreciation_state, "open", "State of the asset should be running"
        )
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 2000,
                    "value_depreciable_residual": 0,
                    "value_salvage": 2000,
                }
            ],
        )
        self.assertRecordValues(
            CEO_car.depreciation_move_ids.sorted(lambda l: l.date),
            [
                {
                    "amount_total": 1000,
                    "asset_remaining_value": 9000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 7000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 5000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 3000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": 1000,
                },
                {
                    "amount_total": 1000,
                    "asset_remaining_value": 0,
                },
            ],
        )

        CEO_car._close(
            self.closing_invoice.invoice_line_ids,
            date=fields.Date.today() + relativedelta(days=30),
        )
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 12000,
                    "value_depreciable_residual": 10000,
                    "value_salvage": 2000,
                }
            ],
        )
        self.assertRecordValues(
            CEO_car.depreciation_move_ids.sorted(lambda l: (l.date, l.id)),
            [
                {
                    "amount_total": 166.67,
                    "asset_remaining_value": 9833.33,
                    "state": "draft",
                },
                {
                    "amount_total": 12000,
                    "asset_remaining_value": 0,
                    "state": "draft",
                },
            ],
        )
        closing_move = max(CEO_car.depreciation_move_ids, key=lambda m: (m.date, m.id))
        self.assertRecordValues(
            closing_move,
            [
                {
                    "date": fields.Date.today() + relativedelta(days=30),
                }
            ],
        )
        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "debit": 0,
                    "credit": 12000,
                    "account_id": CEO_car.account_asset_id.id,
                },
                {
                    "debit": 166.67,
                    "credit": 0,
                    "account_id": CEO_car.account_depreciation_id.id,
                },
                {
                    "debit": 100,
                    "credit": 0,
                    "account_id": self.closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "debit": 11733.33,
                    "credit": 0,
                    "account_id": self.env.company.loss_account_id.id,
                },
            ],
        )
        CEO_car.depreciation_move_ids.auto_post = "no"
        CEO_car.depreciation_move_ids.action_post()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 0,
                    "value_depreciable_residual": 0,
                    "value_salvage": 2000,
                    "depreciation_state": "close",
                }
            ],
        )

    def test_01_account_asset(self):
        account_asset_model = self.env["account.depreciation.profile"].create(
            {
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "name": "Typical car - 3 Years",
                "depreciation_duration": 3,
                "depreciation_period": "12",
                "depreciation_prorata": "daily_computation",
            }
        )

        self.company_data["default_account_assets"].create_asset = "validate"
        self.company_data[
            "default_account_assets"
        ].depreciation_profile_ids = account_asset_model

        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.env["res.partner"]
                .create({"name": "Res Partner 12"})
                .id,
                "invoice_date": "2020-12-31",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Very little red car",
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "price_unit": 450,
                            "quantity": 1,
                        },
                    )
                ],
            }
        )
        invoice.action_post()

        asset = invoice.capitalised_asset_ids
        self.assertEqual(
            len(asset),
            1,
            "One and only one asset should have been created from invoice.",
        )

        self.assertTrue(
            asset.depreciation_state == "open", "Asset should be in Open state"
        )
        first_invoice_line = invoice.invoice_line_ids[0]
        self.assertEqual(
            asset.value_original,
            first_invoice_line.price_subtotal,
            "Asset value is not same as invoice line.",
        )

        first_depreciation_line = asset.depreciation_move_ids.sorted(lambda r: r.id)[0]
        self.assertAlmostEqual(
            first_depreciation_line.asset_remaining_value,
            asset.value_original - first_depreciation_line.amount_total,
            msg="Remaining value is incorrect.",
        )
        self.assertAlmostEqual(
            first_depreciation_line.asset_depreciated_value,
            first_depreciation_line.amount_total,
            msg="Depreciated value is incorrect.",
        )

        last_depreciation_date = first_depreciation_line.date
        installment_date = last_depreciation_date + relativedelta(
            months=+int(asset.depreciation_period)
        )
        self.assertEqual(
            asset.depreciation_move_ids.sorted(lambda r: r.id)[1].date,
            installment_date,
            "Installment date is incorrect.",
        )

    def test_02_account_asset(self):
        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 2000.0,
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "CEO's Car",
                "value_original": 12000.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
                "date_acquisition": "2010-01-31",
                "value_depreciated_import": 10000.0,
            }
        )
        CEO_car._onchange_depreciation_profile_id()

        CEO_car.action_confirm()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 2000,
                    "value_depreciable_residual": 0,
                    "value_salvage": 2000,
                }
            ],
        )
        self.assertFalse(CEO_car.depreciation_move_ids)
        CEO_car._close(self.closing_invoice.invoice_line_ids)
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 2000,
                    "value_depreciable_residual": 0,
                    "value_salvage": 2000,
                }
            ],
        )
        closing_move = CEO_car.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )
        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "debit": 0,
                    "credit": 12000,
                    "account_id": CEO_car.account_asset_id.id,
                },
                {
                    "debit": 10000,
                    "credit": 0,
                    "account_id": CEO_car.account_depreciation_id.id,
                },
                {
                    "debit": 100,
                    "credit": 0,
                    "account_id": self.closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "debit": 1900,
                    "credit": 0,
                    "account_id": CEO_car.company_id.loss_account_id.id,
                },
            ],
        )
        closing_move.action_post()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 0,
                    "value_depreciable_residual": 0,
                    "value_salvage": 2000,
                }
            ],
        )

    def test_03_account_asset(self):
        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 0,
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "CEO's Car",
                "value_original": 12000.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
                "date_acquisition": "2010-01-31",
                "value_depreciated_import": 12000.0,
            }
        )
        CEO_car._onchange_depreciation_profile_id()

        CEO_car.action_confirm()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 0,
                    "value_depreciable_residual": 0,
                    "value_salvage": 0,
                }
            ],
        )
        self.assertFalse(CEO_car.depreciation_move_ids)
        CEO_car._close(self.closing_invoice.invoice_line_ids)
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 0,
                    "value_depreciable_residual": 0,
                    "value_salvage": 0,
                }
            ],
        )
        closing_move = CEO_car.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )
        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "debit": 0,
                    "credit": 12000,
                    "account_id": CEO_car.account_asset_id.id,
                },
                {
                    "debit": 12000,
                    "credit": 0,
                    "account_id": CEO_car.account_depreciation_id.id,
                },
                {
                    "debit": 100,
                    "credit": 0,
                    "account_id": self.closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "debit": 0,
                    "credit": 100,
                    "account_id": CEO_car.company_id.gain_account_id.id,
                },
            ],
        )
        closing_move.action_post()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 0,
                    "value_depreciable_residual": 0,
                    "value_salvage": 0,
                }
            ],
        )

    def test_04_account_asset(self):
        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 0,
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "CEO's Car",
                "value_original": 800.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
                "date_acquisition": "2021-01-01",
                "value_depreciated_import": 300.0,
            }
        )
        CEO_car._onchange_depreciation_profile_id()
        CEO_car.depreciation_duration = 5

        CEO_car.action_confirm()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 800,
                    "value_book": 500,
                    "value_depreciable_residual": 500,
                    "value_salvage": 0,
                }
            ],
        )
        self.assertEqual(len(CEO_car.depreciation_move_ids), 4)
        CEO_car._close(
            self.closing_invoice.invoice_line_ids,
            date=fields.Date.today() + relativedelta(months=-6, days=-1),
        )
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 800,
                    "value_book": 500,
                    "value_depreciable_residual": 500,
                    "value_salvage": 0,
                }
            ],
        )
        closing_move = CEO_car.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )
        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "debit": 0,
                    "credit": 800,
                    "account_id": CEO_car.account_asset_id.id,
                },
                {
                    "debit": 300,
                    "credit": 0,
                    "account_id": CEO_car.account_depreciation_id.id,
                },
                {
                    "debit": 100,
                    "credit": 0,
                    "account_id": self.closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "debit": 400,
                    "credit": 0,
                    "account_id": CEO_car.company_id.loss_account_id.id,
                },
            ],
        )
        closing_move.action_post()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 800,
                    "value_book": 0,
                    "value_depreciable_residual": 0,
                    "value_salvage": 0,
                }
            ],
        )

    def test_05_account_asset(self):
        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 0,
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "CEO's Car",
                "value_original": 1000.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
                "date_acquisition": "2020-01-01",
            }
        )
        CEO_car._onchange_depreciation_profile_id()
        CEO_car.depreciation_duration = 5
        CEO_car.account_depreciation_id = CEO_car.account_asset_id

        CEO_car.action_confirm()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 1000,
                    "value_book": 800,
                    "value_depreciable_residual": 800,
                    "value_salvage": 0,
                }
            ],
        )
        self.assertEqual(len(CEO_car.depreciation_move_ids), 5)
        CEO_car._close(
            self.env["account.move.line"],
            date=fields.Date.today() + relativedelta(days=-1),
        )
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 1000,
                    "value_book": 700,
                    "value_depreciable_residual": 700,
                    "value_salvage": 0,
                }
            ],
        )
        closing_move = CEO_car.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )
        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "debit": 0,
                    "credit": 1000,
                    "account_id": CEO_car.account_asset_id.id,
                },
                {
                    "debit": 300,
                    "credit": 0,
                    "account_id": CEO_car.account_depreciation_id.id,
                },
                {
                    "debit": 700,
                    "credit": 0,
                    "account_id": CEO_car.company_id.loss_account_id.id,
                },
            ],
        )
        closing_move.action_post()
        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 1000,
                    "value_book": 0,
                    "value_depreciable_residual": 0,
                    "value_salvage": 0,
                }
            ],
        )

    def test_06_account_asset(self):
        asset_account = self.env["account.account"].create(
            {
                "name": "test_06_account_asset",
                "code": "test.06.account.asset",
                "account_type": "asset_non_current",
                "create_asset": "no",
                "multiple_assets_per_line": True,
            }
        )

        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 0,
                "depreciation_state": "draft",
                "depreciation_period": "12",
                "depreciation_duration": 4,
                "name": "CEO's Car",
                "value_original": 1000.0,
                "date_acquisition": fields.Date.today() - relativedelta(years=3),
                "account_asset_id": asset_account.id,
                "account_depreciation_id": self.company_data["default_account_assets"]
                .copy()
                .id,
                "account_depreciation_expense_id": asset_account.id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "depreciation_prorata": "none",
            }
        )

        CEO_car.action_confirm()
        posted_entries = len(
            CEO_car.depreciation_move_ids.filtered(lambda x: x.state == "posted")
        )
        self.assertEqual(posted_entries, 3)

        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 1000,
                    "value_book": 250,
                    "value_depreciable_residual": 250,
                    "value_salvage": 0,
                }
            ],
        )

    def test_account_asset_cancel(self):
        today = fields.Date.today()
        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 2000.0,
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "CEO's Car",
                "value_original": 12000.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
                "date_acquisition": today + relativedelta(years=-3, month=1, day=1),
            }
        )
        CEO_car._onchange_depreciation_profile_id()
        CEO_car.depreciation_duration = 5
        CEO_car.action_confirm()

        self.assertRecordValues(
            CEO_car,
            [
                {
                    "value_original": 12000,
                    "value_book": 6000,
                    "value_depreciable_residual": 4000,
                    "value_salvage": 2000,
                }
            ],
        )
        CEO_car.action_cancel()

        self.assertEqual(CEO_car.depreciation_state, "cancelled")
        self.assertFalse(CEO_car.depreciation_move_ids)

        Hashed_car = CEO_car.copy()
        Hashed_car.write(
            {
                "value_original": 12000.0,
                "depreciation_duration": 5,
                "name": "Hashed Car",
                "depreciation_journal_id": CEO_car.depreciation_journal_id.copy().id,
                "date_acquisition": today + relativedelta(years=-3, month=1, day=1),
            }
        )
        Hashed_car.depreciation_journal_id.restrict_mode_hash_table = True
        Hashed_car.action_confirm()
        self.assertTrue(
            False
            not in Hashed_car.depreciation_move_ids._sorted_by_date()[:3].mapped(
                "inalterable_hash"
            )
        )

        for i in range(4):
            self.assertFalse(
                Hashed_car.depreciation_move_ids._sorted_by_date()[i].reversal_move_ids
            )

        Hashed_car.action_cancel()

        self.assertEqual(Hashed_car.depreciation_state, "cancelled")
        for i in range(2):
            self.assertTrue(
                Hashed_car.depreciation_move_ids._sorted_by_date()[
                    i
                ].reversal_move_ids.id
                > 0
                or Hashed_car.depreciation_move_ids._sorted_by_date()[
                    i
                ].reversed_entry_id.id
                > 0
            )

        report = self.env.ref("account_depreciation.assets_report")
        options = self._generate_options(
            report,
            today + relativedelta(years=-6, month=1, day=1),
            today + relativedelta(years=+4, month=12, day=31),
        )
        lines = report._get_lines({**options, "unfold_all": False, "all_entries": True})
        assets_in_report = [x["name"] for x in lines[:-1]]

        self.assertNotIn(CEO_car.name, assets_in_report)
        self.assertNotIn(Hashed_car.name, assets_in_report)

        Locked_car = CEO_car.copy()
        Locked_car.write(
            {
                "value_original": 12000.0,
                "depreciation_duration": 10,
                "name": "Locked Car",
                "date_acquisition": today + relativedelta(years=-3, month=1, day=1),
            }
        )
        Locked_car.action_confirm()
        Locked_car.company_id.fiscalyear_lock_date = today + relativedelta(years=-1)

        self.assertEqual(len(Locked_car.depreciation_move_ids), 10)
        Locked_car.action_cancel()
        self.assertRecordValues(
            Locked_car,
            [
                {
                    "depreciation_state": "cancelled",
                    "value_book": 12000.0,
                    "value_depreciable_residual": 10000,
                    "value_salvage": 2000,
                }
            ],
        )
        self.assertEqual(len(Locked_car.depreciation_move_ids), 4)
        for depreciation in Locked_car.depreciation_move_ids:
            self.assertTrue(
                depreciation.reversal_move_ids or depreciation.reversed_entry_id
            )

    def test_asset_form(self):
        asset_form = Form(
            self.env["resource.asset"].with_context(default_depreciation_state="draft"),
            view="account_depreciation.view_account_asset_form",
        )
        asset_form.name = "Test Asset"
        asset_form.value_original = 10000
        asset_form.account_depreciation_id = self.company_data["default_account_assets"]
        asset_form.account_depreciation_expense_id = self.company_data[
            "default_account_expense"
        ]
        asset_form.depreciation_journal_id = self.company_data["default_journal_misc"]
        asset_form.depreciation_prorata = "none"
        asset = asset_form.save()
        asset.action_confirm()

        self.assertEqual(len(asset.depreciation_move_ids), 5)
        for move in asset.depreciation_move_ids:
            self.assertEqual(move.amount_total, 2000)

        asset_form = Form(asset, view="account_depreciation.view_account_asset_form")
        with self.assertRaises(UserError):
            with asset_form.depreciation_move_ids.edit(4) as line_edit:
                line_edit.depreciation_value = 1000.0
            asset_form.save()

        asset_form = Form(asset, view="account_depreciation.view_account_asset_form")
        with asset_form.depreciation_move_ids.edit(4) as line_edit:
            line_edit.depreciation_value = 1000.0
        with asset_form.depreciation_move_ids.edit(3) as line_edit:
            line_edit.depreciation_value = 3000.0
        self.update_form_values(asset_form)
        asset_form.save()

    def test_negative_asset_balance_inversion(self):
        asset_account = self.company_data["default_account_assets"].id
        expense_account = self.company_data["default_account_expense"].id
        asset = self.env["resource.asset"].create(
            {
                "name": "Test Asset",
                "value_original": -10000,
                "account_depreciation_id": asset_account,
                "account_depreciation_expense_id": expense_account,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "depreciation_prorata": "none",
            }
        )
        asset._create_depreciation_entries()

        self.assertEqual(len(asset.depreciation_move_ids), 5)
        for move in asset.depreciation_move_ids:
            self.assertEqual(move.depreciation_value, -2000)

        with Form(
            asset, view="account_depreciation.view_account_asset_form"
        ) as asset_form:
            with asset_form.depreciation_move_ids.edit(4) as line_edit:
                line_edit.depreciation_value = -1000.0
            with asset_form.depreciation_move_ids.edit(3) as line_edit:
                line_edit.depreciation_value = -3000.0
        self.update_form_values(asset_form)

        self.assertRecordValues(
            asset.depreciation_move_ids._sorted_by_date()[-1].line_ids,
            [
                {"account_id": asset_account, "balance": 1000.0},
                {"account_id": expense_account, "balance": -1000.0},
            ],
        )

        self.assertRecordValues(
            asset.depreciation_move_ids._sorted_by_date()[-2].line_ids,
            [
                {"account_id": asset_account, "balance": 3000.0},
                {"account_id": expense_account, "balance": -3000.0},
            ],
        )

    def test_asset_change_depreciation_expense_account(self):
        self.env["account.move"].search([("state", "=", "draft")]).unlink()
        asset = self.env["resource.asset"].create(
            {
                "name": "Test asset",
                "date_acquisition": "2011-07-01",
                "value_original": 1000.0,
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
            }
        )
        asset.action_confirm()

        sorted_depreciation_moves = asset.depreciation_move_ids.sorted(lambda l: l.date)
        td = fields.Date.to_date
        self.assertRecordValues(
            sorted_depreciation_moves,
            [
                {"date": td("2011-12-31"), "depreciation_value": 100},
                {"date": td("2012-12-31"), "depreciation_value": 200},
                {"date": td("2013-12-31"), "depreciation_value": 200},
                {"date": td("2014-12-31"), "depreciation_value": 200},
                {"date": td("2015-12-31"), "depreciation_value": 200},
                {"date": td("2016-12-31"), "depreciation_value": 100},
            ],
        )

        new_depreciation_expense_account = asset.account_depreciation_expense_id.copy()
        for period, depreciation_move in enumerate(sorted_depreciation_moves):
            with (
                self.subTest(period=period, depreciation_date=depreciation_move.date),
                freeze_time(depreciation_move.date),
            ):
                with self.enter_registry_test_mode():
                    self.env.ref(
                        "account.ir_cron_auto_post_draft_entry"
                    ).method_direct_trigger()

                if period == 3:
                    asset.account_depreciation_expense_id = (
                        new_depreciation_expense_account
                    )

                expense_line = depreciation_move.line_ids.filtered(
                    lambda line: line.account_id.internal_group == "expense"
                )
                if period > 2:
                    self.assertEqual(
                        expense_line.account_id, new_depreciation_expense_account
                    )
                else:
                    self.assertEqual(
                        expense_line.account_id,
                        self.company_data["default_account_expense"],
                    )

                lock_wiz = self.env["account.change.lock.date"].create(
                    {"fiscalyear_lock_date": depreciation_move.date}
                )
                with freeze_time("9999-12-31"):
                    lock_wiz.change_lock_date()

        depreciation_field = self.env["account.move"]._fields["depreciation_value"]
        self.env.add_to_compute(depreciation_field, sorted_depreciation_moves)

        self.assertRecordValues(
            sorted_depreciation_moves,
            [
                {"date": td("2011-12-31"), "depreciation_value": 100},
                {"date": td("2012-12-31"), "depreciation_value": 200},
                {"date": td("2013-12-31"), "depreciation_value": 200},
                {"date": td("2014-12-31"), "depreciation_value": 200},
                {"date": td("2015-12-31"), "depreciation_value": 200},
                {"date": td("2016-12-31"), "depreciation_value": 100},
            ],
        )

    def test_asset_from_entry_line_form(self):

        move_ids = self.env["account.move"].create(
            [
                {
                    "ref": "line1",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                                "debit": 300,
                                "name": "Furniture",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "account_id": self.company_data[
                                    "default_account_assets"
                                ].id,
                                "credit": 300,
                            },
                        ),
                    ],
                },
                {
                    "ref": "line2",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                                "debit": 600,
                                "name": "Furniture too",
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "account_id": self.company_data[
                                    "default_account_assets"
                                ].id,
                                "credit": 600,
                            },
                        ),
                    ],
                },
            ]
        )
        move_ids.action_post()
        move_line_ids = move_ids.mapped("line_ids").filtered(lambda x: x.debit)

        asset_form = Form(
            self.env["resource.asset"].with_context(
                default_depreciation_state="draft",
                default_original_move_line_ids=move_line_ids.ids,
            ),
            view="account_depreciation.view_account_asset_form",
        )
        asset_form.original_move_line_ids = move_line_ids
        asset_form.account_depreciation_expense_id = self.company_data[
            "default_account_expense"
        ]

        asset = asset_form.save()
        self.assertEqual(asset.value_depreciable_residual, 900.0)
        self.assertIn(asset.name, ["Furniture", "Furniture too"])
        self.assertEqual(asset.depreciation_journal_id.type, "general")
        self.assertEqual(
            asset.account_asset_id, self.company_data["default_account_expense"]
        )
        self.assertEqual(
            asset.account_depreciation_id, self.company_data["default_account_expense"]
        )
        self.assertEqual(
            asset.account_depreciation_expense_id,
            self.company_data["default_account_expense"],
        )
        self.assertEqual(asset.date_acquisition, min(move_ids.mapped("date")))

    def test_asset_from_bill_move_line_form(self):

        move_ids = self.env["account.move"].create(
            [
                {
                    "move_type": "in_invoice",
                    "partner_id": self.partner_a.id,
                    "ref": "line1",
                    "date": "2020-06-01",
                    "invoice_date": "2020-06-15",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                                "price_unit": 300,
                                "name": "Furniture",
                                "tax_ids": [],
                            }
                        ),
                    ],
                },
                {
                    "move_type": "in_invoice",
                    "partner_id": self.partner_a.id,
                    "ref": "line2",
                    "date": "2020-06-01",
                    "invoice_date": "2020-06-14",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                                "price_unit": 600,
                                "name": "Furniture too",
                                "tax_ids": [],
                            }
                        ),
                    ],
                },
            ]
        )
        move_ids.action_post()
        move_line_ids = move_ids.mapped("line_ids").filtered(lambda x: x.debit)

        asset_form = Form(
            self.env["resource.asset"].with_context(
                default_depreciation_state="draft",
                default_original_move_line_ids=move_line_ids.ids,
            ),
            view="account_depreciation.view_account_asset_form",
        )
        asset_form.original_move_line_ids = move_line_ids
        asset_form.account_depreciation_expense_id = self.company_data[
            "default_account_expense"
        ]

        asset = asset_form.save()
        self.assertEqual(asset.value_depreciable_residual, 900.0)
        self.assertRecordValues(
            asset,
            [
                {
                    "name": "Furniture",
                    "account_asset_id": self.company_data["default_account_expense"].id,
                    "account_depreciation_id": self.company_data[
                        "default_account_expense"
                    ].id,
                    "account_depreciation_expense_id": self.company_data[
                        "default_account_expense"
                    ].id,
                    "date_acquisition": min(move_ids.mapped("invoice_date")),
                }
            ],
        )

    def test_asset_from_bill_move_line_form_multicurrency(self):

        asset_account = self.company_data["default_account_assets"]
        non_deductible_tax = self.env["account.tax"].create(
            {
                "name": "Non-deductible Tax",
                "amount": 21,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                ],
            }
        )
        asset_account.tax_ids = non_deductible_tax

        asset_account.create_asset = "no"
        asset_account.multiple_assets_per_line = False

        vendor_bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "currency_id": self.other_currency.id,
                "invoice_date": "2020-01-01",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "account_id": asset_account.id,
                            "currency_id": self.other_currency.id,
                            "name": "Asus Laptop",
                            "price_unit": 1000.0,
                            "quantity": 1,
                            "tax_ids": [Command.set(non_deductible_tax.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "account_id": asset_account.id,
                            "currency_id": self.other_currency.id,
                            "name": "Lenovo Laptop",
                            "price_unit": 500.0,
                            "quantity": 1,
                            "tax_ids": [Command.set(non_deductible_tax.ids)],
                        }
                    ),
                ],
            }
        )
        vendor_bill.action_post()
        self.env.flush_all()

        move_line_ids = vendor_bill.mapped("line_ids").filtered(
            lambda x: x.name and "Laptop" in x.name
        )
        asset_form = Form(
            self.env["resource.asset"].with_context(
                default_depreciation_state="draft",
                default_original_move_line_ids=move_line_ids.ids,
                asset_type="purchase",
            ),
            view="account_depreciation.view_account_asset_form",
        )
        asset_form.original_move_line_ids = move_line_ids
        asset_form.account_depreciation_expense_id = self.company_data[
            "default_account_expense"
        ]

        new_assets = asset_form.save()
        self.assertEqual(len(new_assets), 1)
        self.assertEqual(new_assets.value_original, 828.75)
        self.assertEqual(new_assets.value_non_deductible_tax, 78.75)

    def test_asset_modify_value_00(self):
        self.assertEqual(self.truck.value_depreciable_residual, 3000)
        self.assertEqual(self.truck.value_salvage, 2500)

        self.env["asset.modify"].create(
            {
                "name": "New beautiful sticker :D",
                "asset_id": self.truck.id,
                "value_depreciable_residual": 4000,
                "value_salvage": 3000,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
            }
        ).action_modify()
        self.assertEqual(self.truck.value_depreciable_residual, 3000)
        self.assertEqual(self.truck.value_salvage, 2500)
        self.assertEqual(self.truck.increase_ids.value_depreciable_residual, 1000)
        self.assertEqual(self.truck.increase_ids.value_salvage, 500)
        self.assertEqual(
            self.truck.account_depreciation_id.id,
            self.company_data["default_account_assets"].id,
        )

    def test_asset_modify_value_01(self):
        self.env["asset.modify"].create(
            {
                "name": "Accident :'(",
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "asset_id": self.truck.id,
                "value_depreciable_residual": 1000,
                "value_salvage": 2000,
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()
        self.assertEqual(self.truck.value_depreciable_residual, 1000)
        self.assertEqual(self.truck.value_salvage, 2000)
        self.assertEqual(self.truck.increase_ids.value_depreciable_residual, 0)
        self.assertEqual(self.truck.increase_ids.value_salvage, 0)
        self.assertEqual(
            max(
                self.truck.depreciation_move_ids.filtered(
                    lambda m: m.state == "posted"
                ),
                key=lambda m: (m.date, m.id),
            ).amount_total,
            2500,
        )

    def test_asset_modify_value_02(self):
        self.env["asset.modify"].create(
            {
                "name": "Don't wanna depreciate all of it",
                "asset_id": self.truck.id,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "value_depreciable_residual": 1000,
                "value_salvage": 4500,
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()
        self.assertEqual(self.truck.value_depreciable_residual, 1000)
        self.assertEqual(self.truck.value_salvage, 4500)
        self.assertEqual(self.truck.increase_ids.value_depreciable_residual, 0)
        self.assertEqual(self.truck.increase_ids.value_salvage, 0)

    def test_asset_modify_value_03(self):
        self.env["asset.modify"].create(
            {
                "name": "Some aliens did something to my truck",
                "asset_id": self.truck.id,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "value_depreciable_residual": 1000,
                "value_salvage": 6000,
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()
        self.assertEqual(self.truck.value_depreciable_residual, 1000)
        self.assertEqual(self.truck.value_salvage, 4500)
        self.assertEqual(self.truck.increase_ids.value_depreciable_residual, 0)
        self.assertEqual(self.truck.increase_ids.value_salvage, 1500)

    def test_asset_modify_value_04(self):
        self.env["asset.modify"].create(
            {
                "name": "GODZILA IS REAL!",
                "asset_id": self.truck.id,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "value_depreciable_residual": 4000,
                "value_salvage": 2000,
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()
        self.assertEqual(self.truck.value_depreciable_residual, 3500)
        self.assertEqual(self.truck.value_salvage, 2000)
        self.assertEqual(self.truck.increase_ids.value_depreciable_residual, 500)
        self.assertEqual(self.truck.increase_ids.value_salvage, 0)

    def test_asset_modify_report(self):

        today = fields.Date.today()

        report = self.env.ref("account_depreciation.assets_report")
        options = self._generate_options(
            report,
            today + relativedelta(years=-6, month=1, day=1),
            today + relativedelta(years=+4, month=12, day=31),
        )
        lines = report._get_lines({**options, "unfold_all": False, "all_entries": True})
        self.assertListEqual(
            [0.0, 10000.0, 0.0, 10000.0, 0.0, 7500.0, 0.0, 7500.0, 2500.0],
            [x["no_format"] for x in lines[0]["columns"][3:]],
        )

        options = self._generate_options(
            report,
            today + relativedelta(years=-6, month=1, day=1),
            today + relativedelta(years=+4, month=12, day=31),
        )
        lines = report._get_lines(
            {**options, "unfold_all": False, "all_entries": False}
        )
        self.assertListEqual(
            [0.0, 10000.0, 0.0, 10000.0, 0.0, 4500.0, 0.0, 4500.0, 5500.0],
            [x["no_format"] for x in lines[0]["columns"][3:]],
        )

        options = self._generate_options(
            report,
            today + relativedelta(years=0, month=1, day=1),
            today + relativedelta(years=0, month=12, day=31),
        )
        lines = report._get_lines({**options, "unfold_all": False, "all_entries": True})
        self.assertListEqual(
            [10000.0, 0.0, 0.0, 10000.0, 4500.0, 750.0, 0.0, 5250.0, 4750.0],
            [x["no_format"] for x in lines[0]["columns"][3:]],
        )

        self.assertEqual(self.truck.value_depreciable_residual, 3000)
        self.assertEqual(self.truck.value_salvage, 2500)
        self.env["asset.modify"].create(
            {
                "name": "New beautiful sticker :D",
                "asset_id": self.truck.id,
                "date": fields.Date.today()
                + relativedelta(years=-1, months=-6, days=-1),
                "value_depreciable_residual": 4750,
                "value_salvage": 3000,
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()

        self.assertEqual(
            self.truck.value_depreciable_residual
            + sum(self.truck.increase_ids.mapped("value_depreciable_residual")),
            3800,
        )
        self.assertEqual(
            self.truck.value_salvage
            + sum(self.truck.increase_ids.mapped("value_salvage")),
            3000,
        )

        options = self._generate_options(
            report,
            today + relativedelta(years=-6, months=-6),
            today + relativedelta(years=+4, month=12, day=31),
        )
        lines = report._get_lines({**options, "unfold_all": False, "all_entries": True})
        self.assertListEqual(
            [0.0, 11500.0, 0.0, 11500.0, 0.0, 8500.0, 0.0, 8500.0, 3000.0],
            [x["no_format"] for x in lines[0]["columns"][3:]],
        )
        self.assertEqual(
            "10 y", lines[1]["columns"][2]["name"], "Depreciation Rate = 10%"
        )

        options = self._generate_options(
            report,
            today + relativedelta(years=0, month=1, day=1),
            today + relativedelta(years=0, month=12, day=31),
        )
        lines = report._get_lines({**options, "unfold_all": False, "all_entries": True})
        self.assertListEqual(
            [11500.0, 0.0, 0.0, 11500.0, 4700.0, 950.0, 0.0, 5650.0, 5850.0],
            [x["no_format"] for x in lines[0]["columns"][3:]],
        )

        self.env["asset.modify"].create(
            {
                "name": "Huge scratch on beautiful sticker :'( It is ruined",
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "asset_id": self.truck.increase_ids.id,
                "value_depreciable_residual": 0,
                "value_salvage": 500,
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()
        self.env["asset.modify"].create(
            {
                "name": "Huge scratch on beautiful sticker :'( It went through...",
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "asset_id": self.truck.id,
                "value_depreciable_residual": 1000,
                "value_salvage": 2500,
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()
        self.assertEqual(
            self.truck.value_depreciable_residual
            + sum(self.truck.increase_ids.mapped("value_depreciable_residual")),
            1000,
        )
        self.assertEqual(
            self.truck.value_salvage
            + sum(self.truck.increase_ids.mapped("value_salvage")),
            3000,
        )

        options = self._generate_options(
            report,
            today + relativedelta(years=-6, month=1, day=1),
            today + relativedelta(years=+4, month=12, day=31),
        )
        lines = report._get_lines({**options, "unfold_all": False, "all_entries": True})
        self.assertListEqual(
            [0.0, 11500.0, 0.0, 11500.0, 0.0, 8500.0, 0.0, 8500.0, 3000.0],
            [x["no_format"] for x in lines[0]["columns"][3:]],
        )

        options = self._generate_options(
            report,
            today + relativedelta(years=-1, month=1, day=1),
            today + relativedelta(years=-1, month=12, day=31),
        )
        lines = report._get_lines({**options, "unfold_all": False, "all_entries": True})
        self.assertListEqual(
            [10000.0, 1500.0, 0.0, 11500.0, 3750.0, 3750.0, 0.0, 7500.0, 4000.0],
            [x["no_format"] for x in lines[0]["columns"][3:]],
        )

    def test_asset_pause_resume(self):
        today = fields.Date.today()
        self.assertEqual(
            len(
                self.truck.depreciation_move_ids.filtered(lambda e: e.state == "draft")
            ),
            4,
        )
        self.env["asset.modify"].create(
            {
                "date": fields.Date.today() + relativedelta(days=-1),
                "asset_id": self.truck.id,
            }
        ).action_pause()
        self.assertEqual(
            len(
                self.truck.depreciation_move_ids.filtered(lambda e: e.state == "draft")
            ),
            0,
        )
        with freeze_time(today) as frozen_time:
            frozen_time.move_to(today + relativedelta(years=1))
            self.env["asset.modify"].with_context(resume_after_pause=True).create(
                {
                    "asset_id": self.truck.id,
                }
            ).action_modify()
            self.assertEqual(
                len(
                    self.truck.depreciation_move_ids.filtered(
                        lambda e: e.state == "posted"
                    )
                ),
                7,
            )
            self.assertEqual(
                self.truck.depreciation_move_ids.filtered(lambda e: e.state == "draft")
                .sorted(lambda move: (move.date, move.id))
                .mapped("amount_total"),
                [375.0, 750.0, 750.0, 750.0],
            )

    def test_asset_modify_sell_profit(self):
        closing_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    (0, 0, {"price_unit": self.truck.value_book + 100})
                ],
            }
        )
        self.env["asset.modify"].create(
            {
                "asset_id": self.truck.id,
                "invoice_line_ids": closing_invoice.invoice_line_ids,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "modify_action": "sell",
            }
        ).action_sell_dispose()

        closing_move = self.truck.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )
        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "ref": "truck: Sale",
                    "debit": 0,
                    "credit": 10000,
                    "account_id": self.truck.account_asset_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 4500,
                    "credit": 0,
                    "account_id": self.truck.account_depreciation_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 5600,
                    "credit": 0,
                    "account_id": closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 0,
                    "credit": 100,
                    "account_id": self.env.company.gain_account_id.id,
                },
            ],
        )

    def test_asset_modify_sell_loss(self):
        closing_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    (0, 0, {"price_unit": self.truck.value_book - 100})
                ],
            }
        )
        self.env["asset.modify"].create(
            {
                "asset_id": self.truck.id,
                "invoice_line_ids": closing_invoice.invoice_line_ids,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "modify_action": "sell",
            }
        ).action_sell_dispose()
        closing_move = self.truck.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )

        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "ref": "truck: Sale",
                    "debit": 0,
                    "credit": 10000,
                    "account_id": self.truck.account_asset_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 4500,
                    "credit": 0,
                    "account_id": self.truck.account_depreciation_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 5400,
                    "credit": 0,
                    "account_id": closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 100,
                    "credit": 0,
                    "account_id": self.env.company.loss_account_id.id,
                },
            ],
        )

    def test_asset_sale_same_account_as_invoice(self):
        closing_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "account_id": self.truck.account_depreciation_id.id,
                            "price_unit": self.truck.value_book - 100,
                        }
                    )
                ],
            }
        )
        self.env["asset.modify"].create(
            {
                "asset_id": self.truck.id,
                "invoice_line_ids": closing_invoice.invoice_line_ids,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "modify_action": "sell",
            }
        ).action_sell_dispose()
        closing_move = self.truck.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )
        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "ref": "truck: Sale",
                    "debit": 0,
                    "credit": 10000,
                    "account_id": self.truck.account_asset_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 4500,
                    "credit": 0,
                    "account_id": self.truck.account_depreciation_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 5400,
                    "credit": 0,
                    "account_id": closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 100,
                    "credit": 0,
                    "account_id": self.env.company.loss_account_id.id,
                },
            ],
        )

        self.assertEqual(
            closing_move.depreciation_value,
            3000,
            "Should be the remaining amount before the sale",
        )

    def test_asset_modify_dispose(self):
        self.env["asset.modify"].create(
            {
                "asset_id": self.truck.id,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "modify_action": "dispose",
            }
        ).action_sell_dispose()
        closing_move = self.truck.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )
        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "ref": "truck: Disposal",
                    "debit": 0,
                    "credit": 10000,
                    "account_id": self.truck.account_asset_id.id,
                },
                {
                    "ref": "truck: Disposal",
                    "debit": 4500,
                    "credit": 0,
                    "account_id": self.truck.account_depreciation_id.id,
                },
                {
                    "ref": "truck: Disposal",
                    "debit": 5500,
                    "credit": 0,
                    "account_id": self.env.company.loss_account_id.id,
                },
            ],
        )

    def test_asset_reverse_depreciation(self):

        self.assertEqual(
            sum(
                self.truck.depreciation_move_ids.filtered(
                    lambda m: m.state == "posted"
                ).mapped("depreciation_value")
            ),
            4500,
        )
        self.assertEqual(
            sum(
                self.truck.depreciation_move_ids.filtered(
                    lambda m: m.state == "draft"
                ).mapped("depreciation_value")
            ),
            3000,
        )
        self.assertEqual(
            max(
                self.truck.depreciation_move_ids.filtered(
                    lambda m: m.state == "posted"
                ),
                key=lambda m: m.date,
            ).asset_remaining_value,
            3000,
        )

        report = self.env.ref("account_depreciation.assets_report")
        today = fields.Date.today()

        move_to_reverse = self.truck.depreciation_move_ids.filtered(
            lambda m: m.state == "posted"
        ).sorted(lambda m: m.date)[-1]
        reversed_move = move_to_reverse._reverse_moves()

        min_date_draft = min(
            self.truck.depreciation_move_ids.filtered(
                lambda m: m.state == "draft" and m.date > reversed_move.date
            ),
            key=lambda m: m.date,
        )
        self.assertEqual(
            move_to_reverse.asset_remaining_value
            - min_date_draft.depreciation_value
            - reversed_move.depreciation_value,
            min_date_draft.asset_remaining_value,
        )
        self.assertEqual(
            move_to_reverse.asset_depreciated_value
            + min_date_draft.depreciation_value
            + reversed_move.depreciation_value,
            min_date_draft.asset_depreciated_value,
        )

        self.assertEqual(
            sum(
                self.truck.depreciation_move_ids.filtered(
                    lambda m: m.state == "posted"
                ).mapped("depreciation_value")
            ),
            4500,
        )
        self.assertEqual(
            sum(
                self.truck.depreciation_move_ids.filtered(
                    lambda m: m.state == "draft"
                ).mapped("depreciation_value")
            ),
            3000,
        )

        self.assertEqual(
            max(
                self.truck.depreciation_move_ids, key=lambda m: m.date
            ).asset_remaining_value,
            0,
        )
        self.assertEqual(
            max(
                self.truck.depreciation_move_ids, key=lambda m: m.date
            ).asset_depreciated_value,
            7500,
        )

        reversed_move.action_post()

        options = self._generate_options(
            report,
            today + relativedelta(years=0, month=7, day=1),
            today + relativedelta(years=0, month=7, day=31),
        )
        lines = report._get_lines({**options, "unfold_all": False, "all_entries": True})
        self.assertListEqual(
            [10000.0, 0.0, 0.0, 10000.0, 4500.0, -750.0, 0.0, 3750.0, 6250.0],
            [x["no_format"] for x in lines[0]["columns"][3:]],
        )

        options = self._generate_options(
            report,
            today + relativedelta(years=0, month=1, day=1),
            today + relativedelta(years=0, month=12, day=31),
        )
        lines = report._get_lines({**options, "unfold_all": False, "all_entries": True})
        self.assertListEqual(
            [10000.0, 0.0, 0.0, 10000.0, 4500.0, 750.0, 0.0, 5250.0, 4750.0],
            [x["no_format"] for x in lines[0]["columns"][3:]],
        )

    def test_ref_asset_depreciation(self):

        for ref in self.truck.depreciation_move_ids.mapped("ref"):
            self.assertEqual(ref, "truck: Depreciation")

    def test_credit_note_out_refund(self):
        depreciation_account = self.company_data["default_account_assets"].copy()
        revenue_model = self.env["account.depreciation.profile"].create(
            {
                "account_depreciation_id": depreciation_account.id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_revenue"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "name": "Hardware - 5 Years",
                "depreciation_duration": 5,
                "depreciation_period": "12",
            }
        )

        depreciation_account.write(
            {"create_asset": "draft", "depreciation_profile_ids": revenue_model}
        )

        invoice = self.env["account.move"].create(
            {
                "invoice_date": "2019-07-01",
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Hardware",
                            "account_id": depreciation_account.id,
                            "price_unit": 5000,
                            "quantity": 1,
                            "tax_ids": False,
                        },
                    )
                ],
            }
        )

        invoice.action_post()
        self.assertTrue(invoice.capitalised_asset_ids)

        credit_note = invoice._reverse_moves([{"invoice_date": fields.Date.today()}])
        credit_note.action_post()

        invoice_asset = invoice.capitalised_asset_ids
        credit_note_asset = credit_note.capitalised_asset_ids

        self.assertTrue(invoice_asset)
        self.assertTrue(credit_note_asset)

        (invoice_asset + credit_note_asset).action_confirm()

        self.assertRecordValues(
            credit_note_asset,
            [
                {
                    "date_acquisition": invoice_asset.date_acquisition,
                    "value_book": -invoice_asset.value_book,
                    "value_depreciable_residual": -invoice_asset.value_depreciable_residual,
                }
            ],
        )

        for invoice_asset_move, credit_note_asset_move in zip(
            invoice_asset.depreciation_move_ids.sorted("date"),
            credit_note_asset.depreciation_move_ids.sorted("date"),
            strict=False,
        ):
            self.assertRecordValues(
                credit_note_asset_move,
                [
                    {
                        "date": invoice_asset_move.date,
                        "state": invoice_asset_move.state,
                        "depreciation_value": -invoice_asset_move.depreciation_value,
                    }
                ],
            )

    def test_asset_multiple_assets_from_one_move_line_00(self):

        account = self.env["account.account"].create(
            {
                "name": "test account",
                "code": "TEST",
                "account_type": "asset_non_current",
                "create_asset": "draft",
                "multiple_assets_per_line": True,
            }
        )
        move = self.env["account.move"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "Johny"}).id,
                "ref": "line1",
                "move_type": "in_invoice",
                "invoice_date": "2020-12-31",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": account.id,
                            "price_unit": 400.0,
                            "name": "stuff",
                            "quantity": 2,
                            "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                            "tax_ids": [],
                        },
                    ),
                ],
            }
        )
        move.action_post()
        assets = move.capitalised_asset_ids
        assets = sorted(assets, key=lambda i: i["value_original"], reverse=True)
        self.assertEqual(len(assets), 2, "2 assets should have been created")
        self.assertEqual(assets[0].value_original, 400.0)
        self.assertEqual(assets[1].value_original, 400.0)

    def test_asset_multiple_assets_from_one_move_line_01(self):

        account = self.env["account.account"].create(
            {
                "name": "test account",
                "code": "TEST",
                "account_type": "asset_non_current",
                "create_asset": "draft",
                "multiple_assets_per_line": True,
            }
        )
        move = self.env["account.move"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "Johny"}).id,
                "ref": "line1",
                "move_type": "in_invoice",
                "invoice_date": "2020-12-31",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": account.id,
                            "name": "stuff",
                            "quantity": 3.0,
                            "price_unit": 1000.0,
                            "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "name": "stuff",
                            "quantity": 1.0,
                            "price_unit": -500.0,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        self.assertEqual(
            sum(asset.value_original for asset in move.capitalised_asset_ids),
            move.line_ids[0].debit,
        )

    def test_asset_credit_note(self):
        asset_model = self.env["account.depreciation.profile"].create(
            {
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "account_asset_id": self.company_data["default_account_assets"].id,
                "depreciation_journal_id": self.company_data[
                    "default_journal_purchase"
                ].id,
                "name": "Small car - 3 Years",
                "depreciation_duration": 3,
                "depreciation_period": "12",
            }
        )

        self.company_data["default_account_assets"].create_asset = "validate"
        self.company_data[
            "default_account_assets"
        ].depreciation_profile_ids = asset_model

        invoice = self.env["account.move"].create(
            {
                "move_type": "in_refund",
                "invoice_date": "2020-01-01",
                "date": "2020-01-01",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Very little red car",
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "price_unit": 450,
                            "quantity": 1,
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        depreciation_lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", asset_model.account_depreciation_id.id),
                (
                    "move_id.depreciation_asset_id",
                    "=",
                    invoice.capitalised_asset_ids.id,
                ),
                ("debit", "=", 150),
            ]
        )
        self.assertEqual(
            len(depreciation_lines),
            3,
            "Three entries with a debit of 150 must be created on the Deferred Expense Account",
        )

    def test_asset_partial_credit_note(self):
        asset_model = self.env["account.depreciation.profile"].create(
            {
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_sale"].id,
                "name": "Maintenance Contract - 3 Years",
                "depreciation_duration": 3,
                "depreciation_period": "12",
                "depreciation_prorata": "none",
            }
        )
        self.company_data["default_account_assets"].create_asset = "draft"
        self.company_data[
            "default_account_assets"
        ].depreciation_profile_ids = asset_model
        account_assets_multiple = self.company_data["default_account_assets"].copy()
        account_assets_multiple.multiple_assets_per_line = True

        product_a = self.env["product.product"].create(
            {
                "name": "Product A",
                "default_code": "PA",
                "lst_price": 100.0,
                "standard_price": 100.0,
            }
        )
        product_b = self.env["product.product"].create(
            {
                "name": "Product B",
                "default_code": "PB",
                "lst_price": 200.0,
                "standard_price": 200.0,
            }
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "invoice_date": "2020-01-01",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product_b.id,
                            "name": "Product B",
                            "account_id": account_assets_multiple.id,
                            "price_unit": 200.0,
                            "quantity": 4,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": product_a.id,
                            "name": "Product A",
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "price_unit": 100.0,
                            "quantity": 7,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": product_a.id,
                            "name": "Product A",
                            "account_id": account_assets_multiple.id,
                            "price_unit": 100.0,
                            "quantity": 5,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": product_a.id,
                            "name": "Product A",
                            "account_id": account_assets_multiple.id,
                            "price_unit": 150.0,
                            "quantity": 6,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": product_a.id,
                            "name": "Product A",
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "price_unit": 100.0,
                            "quantity": 7,
                        },
                    ),
                ],
            }
        )
        invoice.action_post()
        product_a_100_lines = invoice.line_ids.filtered(
            lambda l: l.product_id == product_a and l.price_unit == 100.0
        )
        product_a_150_lines = invoice.line_ids.filtered(
            lambda l: l.product_id == product_a and l.price_unit == 150.0
        )
        product_b_lines = invoice.line_ids.filtered(lambda l: l.product_id == product_b)
        self.assertEqual(
            len(invoice.line_ids.mapped(lambda l: l.capitalised_asset_ids)), 17
        )
        self.assertEqual(len(product_b_lines.capitalised_asset_ids), 4)
        self.assertEqual(len(product_a_100_lines.capitalised_asset_ids), 7)
        self.assertEqual(len(product_a_150_lines.capitalised_asset_ids), 6)
        credit_note = invoice._reverse_moves()
        with Form(credit_note) as move_form:
            move_form.invoice_date = move_form.date
            move_form.invoice_line_ids.remove(0)
            move_form.invoice_line_ids.remove(0)
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.quantity = 1
            with move_form.invoice_line_ids.edit(1) as line_form:
                line_form.quantity = 2
        credit_note.action_post()
        self.assertEqual(
            len(invoice.line_ids.mapped(lambda l: l.capitalised_asset_ids)), 17
        )
        self.assertEqual(len(product_b_lines.capitalised_asset_ids), 4)
        self.assertEqual(len(product_a_100_lines.capitalised_asset_ids), 7)
        self.assertEqual(len(product_a_150_lines.capitalised_asset_ids), 6)

    def test_asset_with_non_deductible_tax(self):

        asset_account = self.company_data["default_account_assets"]
        non_deductible_tax = self.env["account.tax"].create(
            {
                "name": "Non-deductible Tax",
                "amount": 21,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                ],
            }
        )
        asset_account.tax_ids = non_deductible_tax

        asset_account.create_asset = "draft"
        asset_account.depreciation_profile_ids = self.account_asset_model_fixedassets
        asset_account.multiple_assets_per_line = True

        vendor_bill_auto = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "invoice_date": "2020-01-01",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "account_id": asset_account.id,
                            "name": "Asus Laptop",
                            "price_unit": 1000.0,
                            "quantity": 2,
                            "tax_ids": [Command.set(non_deductible_tax.ids)],
                        }
                    )
                ],
            }
        )
        vendor_bill_auto.action_post()

        new_assets_auto = vendor_bill_auto.capitalised_asset_ids
        self.assertEqual(len(new_assets_auto), 2)
        self.assertEqual(new_assets_auto.mapped("value_original"), [1105.0, 1105.0])
        self.assertEqual(
            new_assets_auto.mapped("value_non_deductible_tax"), [105.0, 105.0]
        )

        asset_account.create_asset = "no"
        asset_account.depreciation_profile_ids = None
        asset_account.multiple_assets_per_line = False

        vendor_bill_manu = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "invoice_date": "2020-01-01",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "account_id": asset_account.id,
                            "name": "Asus Laptop",
                            "price_unit": 1000.0,
                            "quantity": 2,
                            "tax_ids": [Command.set(non_deductible_tax.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "account_id": asset_account.id,
                            "name": "Lenovo Laptop",
                            "price_unit": 500.0,
                            "quantity": 3,
                            "tax_ids": [Command.set(non_deductible_tax.ids)],
                        }
                    ),
                ],
            }
        )
        vendor_bill_manu.action_post()

        self.env.flush_all()

        move_line_ids = vendor_bill_manu.mapped("line_ids").filtered(
            lambda x: x.name and "Laptop" in x.name
        )
        asset_form = Form(
            self.env["resource.asset"].with_context(
                default_depreciation_state="draft",
                default_original_move_line_ids=move_line_ids.ids,
            ),
            view="account_depreciation.view_account_asset_form",
        )
        asset_form.original_move_line_ids = move_line_ids
        asset_form.account_depreciation_expense_id = self.company_data[
            "default_account_expense"
        ]

        new_assets_manu = asset_form.save()
        self.assertEqual(len(new_assets_manu), 1)
        self.assertEqual(new_assets_manu.value_original, 3867.5)
        self.assertEqual(new_assets_manu.value_non_deductible_tax, 367.5)

    def test_asset_degressive_01(self):
        asset = self.env["resource.asset"].create(
            {
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "name": "Degressive",
                "date_acquisition": "2021-07-01",
                "depreciation_prorata": "constant_periods",
                "value_original": 10000,
                "depreciation_duration": 5,
                "depreciation_period": "12",
                "depreciation_method": "degressive",
                "depreciation_factor": 0.5,
            }
        )

        asset.action_confirm()

        self.assertEqual(
            asset.depreciation_duration + 1, len(asset.depreciation_move_ids)
        )

        self.assertRecordValues(
            asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)),
            [
                {
                    "amount_total": 2500,
                    "asset_remaining_value": 7500,
                },
                {
                    "amount_total": 3750,
                    "asset_remaining_value": 3750,
                },
                {
                    "amount_total": 1875,
                    "asset_remaining_value": 1875,
                },
                {
                    "amount_total": 937.5,
                    "asset_remaining_value": 937.5,
                },
                {
                    "amount_total": 625.00,
                    "asset_remaining_value": 312.50,
                },
                {
                    "amount_total": 312.50,
                    "asset_remaining_value": 0,
                },
            ],
        )

    def test_asset_degressive_02(self):
        asset = self.env["resource.asset"].create(
            {
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "name": "Degressive",
                "date_acquisition": "2021-01-01",
                "value_original": 10000,
                "depreciation_duration": 5,
                "depreciation_period": "12",
                "depreciation_method": "degressive",
                "depreciation_factor": 0.5,
            }
        )

        asset.action_confirm()

        self.assertEqual(asset.depreciation_duration, len(asset.depreciation_move_ids))

        self.assertRecordValues(
            asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)),
            [
                {
                    "amount_total": 5000,
                    "asset_remaining_value": 5000,
                },
                {
                    "amount_total": 2500,
                    "asset_remaining_value": 2500,
                },
                {
                    "amount_total": 1250,
                    "asset_remaining_value": 1250,
                },
                {
                    "amount_total": 625,
                    "asset_remaining_value": 625,
                },
                {
                    "amount_total": 625,
                    "asset_remaining_value": 0,
                },
            ],
        )

    def test_asset_negative_01(self):
        asset = self.env["resource.asset"].create(
            {
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "name": "Degressive Linear",
                "date_acquisition": "2021-07-01",
                "value_original": -10000,
                "depreciation_duration": 5,
                "depreciation_period": "12",
                "depreciation_method": "linear",
            }
        )
        asset.depreciation_prorata = "constant_periods"

        asset.action_confirm()

        self.assertRecordValues(
            asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)),
            [
                {
                    "amount_total": 1000,
                    "asset_remaining_value": -9000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": -7000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": -5000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": -3000,
                },
                {
                    "amount_total": 2000,
                    "asset_remaining_value": -1000,
                },
                {
                    "amount_total": 1000,
                    "asset_remaining_value": 0,
                },
            ],
        )

    def test_asset_daily_computation_01(self):
        asset = self.env["resource.asset"].create(
            {
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "name": "Degressive Linear",
                "date_acquisition": "2021-07-01",
                "depreciation_prorata": "daily_computation",
                "value_original": 10000,
                "depreciation_duration": 5,
                "depreciation_period": "12",
                "depreciation_method": "linear",
            }
        )

        asset.action_confirm()

        self.assertRecordValues(
            asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)),
            [
                {
                    "amount_total": 1007.67,
                    "asset_remaining_value": 8992.33,
                },
                {
                    "amount_total": 1998.90,
                    "asset_remaining_value": 6993.43,
                },
                {
                    "amount_total": 1998.91,
                    "asset_remaining_value": 4994.52,
                },
                {
                    "amount_total": 2004.38,
                    "asset_remaining_value": 2990.14,
                },
                {
                    "amount_total": 1998.90,
                    "asset_remaining_value": 991.24,
                },
                {
                    "amount_total": 991.24,
                    "asset_remaining_value": 0,
                },
            ],
        )

    def test_decrement_book_value_with_negative_asset(self):
        depreciation_account = self.company_data["default_account_assets"].copy()
        asset_model = self.env["account.depreciation.profile"].create(
            {
                "name": "test",
                "active": True,
                "depreciation_method": "linear",
                "depreciation_duration": 5,
                "depreciation_period": "1",
                "depreciation_prorata": "constant_periods",
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": depreciation_account.id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data[
                    "default_journal_purchase"
                ].id,
            }
        )

        depreciation_account.can_create_asset = True
        depreciation_account.create_asset = "draft"
        depreciation_account.depreciation_profile_ids = asset_model

        refund = self.env["account.move"].create(
            {
                "move_type": "in_refund",
                "partner_id": self.partner_a.id,
                "invoice_date": "2021-06-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "refund",
                            "account_id": depreciation_account.id,
                            "price_unit": 500,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        refund.action_post()

        self.assertTrue(refund.capitalised_asset_ids)

        asset = refund.capitalised_asset_ids

        self.assertEqual(asset.value_book, -refund.amount_total)
        self.assertEqual(asset.value_depreciable_residual, -refund.amount_total)

        asset.action_confirm()

        self.assertEqual(
            len(asset.depreciation_move_ids.filtered(lambda m: m.state == "posted")), 1
        )
        self.assertEqual(asset.value_book, -400.0)
        self.assertEqual(asset.value_depreciable_residual, -400.0)

    def test_depreciation_schedule_report_with_negative_asset(self):
        asset = self.env["resource.asset"].create(
            {
                "name": "test",
                "value_original": -500,
                "depreciation_method": "linear",
                "depreciation_duration": 5,
                "depreciation_period": "1",
                "date_acquisition": fields.Date.today() + relativedelta(months=-1),
                "depreciation_prorata": "none",
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
            }
        )

        asset.action_confirm()

        report = self.env.ref("account_depreciation.assets_report")

        options = self._generate_options(
            report,
            fields.Date.today() + relativedelta(months=-7, day=1),
            fields.Date.today() + relativedelta(months=-6, day=31),
        )

        expected_values_open_asset = [
            ("test", 0, 0, 500.0, -500.0, 0, 0, 100.0, -100.0, -400.0),
        ]

        self.assertLinesValues(
            report._get_lines(options)[2:3],
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            expected_values_open_asset,
            options,
        )

        expense_account_copy = self.company_data["default_account_expense"].copy()

        disposal_action_view = (
            self.env["asset.modify"]
            .create(
                {
                    "asset_id": asset.id,
                    "modify_action": "dispose",
                    "loss_account_id": expense_account_copy.id,
                    "date": fields.Date.today(),
                }
            )
            .action_sell_dispose()
        )

        self.env["account.move"].browse(disposal_action_view["res_id"]).action_post()

        expected_values_closed_asset = [
            ("test", 0, 500.0, 500.0, 0, 0, 500.0, 500.0, 0, 0),
        ]
        options = self._generate_options(
            report,
            fields.Date.today() + relativedelta(months=-7, day=1),
            fields.Date.today(),
        )
        self.assertLinesValues(
            report._get_lines(options)[2:3],
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            expected_values_closed_asset,
            options,
        )

    def test_depreciation_schedule_hierarchy(self):
        assets = self.env["resource.asset"].search(
            [
                ("company_id", "=", self.env.company.id),
            ]
        )
        assets.depreciation_state = "draft"
        assets.mapped("depreciation_move_ids").state = "draft"
        assets.unlink()

        self.env["account.group"].create(
            [
                {"name": "Group 1", "code_prefix_start": "1", "code_prefix_end": "1"},
                {
                    "name": "Group 11",
                    "code_prefix_start": "11",
                    "code_prefix_end": "11",
                },
                {
                    "name": "Group 12",
                    "code_prefix_start": "12",
                    "code_prefix_end": "12",
                },
            ]
        )

        account_a, account_a1, account_b, account_c, account_d, account_e = self.env[
            "account.account"
        ].create(
            [
                {
                    "code": "1100",
                    "name": "Account A",
                    "account_type": "asset_non_current",
                },
                {
                    "code": "1110",
                    "name": "Account A1",
                    "account_type": "asset_non_current",
                },
                {
                    "code": "1200",
                    "name": "Account B",
                    "account_type": "asset_non_current",
                },
                {
                    "code": "1300",
                    "name": "Account C",
                    "account_type": "asset_non_current",
                },
                {
                    "code": "1400",
                    "name": "Account D",
                    "account_type": "asset_non_current",
                },
                {
                    "code": "9999",
                    "name": "Account E",
                    "account_type": "asset_non_current",
                },
            ]
        )

        self.env["resource.asset"].create(
            [
                {
                    "account_asset_id": account_id,
                    "account_depreciation_id": account_id,
                    "account_depreciation_expense_id": self.company_data[
                        "default_account_expense"
                    ].id,
                    "depreciation_journal_id": self.company_data[
                        "default_journal_misc"
                    ].id,
                    "name": name,
                    "date_acquisition": fields.Date.to_date("2020-07-01"),
                    "value_original": value_original,
                    "depreciation_method": "linear",
                    "depreciation_prorata": "none",
                }
                for account_id, name, value_original in [
                    (account_a.id, "ZenBook", 1250),
                    (account_a.id, "ThinkBook", 1500),
                    (account_a1.id, "XPS", 1750),
                    (account_b.id, "MacBook", 2000),
                    (account_c.id, "Aspire", 1600),
                    (account_d.id, "Playstation", 550),
                    (account_e.id, "Xbox", 500),
                ]
            ]
        ).action_confirm()

        report = self.env.ref("account_depreciation.assets_report")
        options = self._generate_options(report, "2022-01-01", "2022-12-31")
        options["hierarchy"] = True
        self.env.company.totals_below_sections = True

        lines = [
            {
                "name": line["name"],
                "level": line["level"],
                "value_book": line["columns"][-1]["name"],
            }
            for line in (report._get_lines(options))
        ]

        expected_values = [
            {"name": "1 Group 1", "level": 1, "value_book": "$\xa06,920.00"},
            {"name": "11 Group 11", "level": 2, "value_book": "$\xa03,600.00"},
            {"name": "1100 Account A", "level": 3, "value_book": "$\xa02,200.00"},
            {"name": "ZenBook", "level": 4, "value_book": "$\xa01,000.00"},
            {"name": "ThinkBook", "level": 4, "value_book": "$\xa01,200.00"},
            {"name": "Total 1100 Account A", "level": 3, "value_book": "$\xa02,200.00"},
            {"name": "1110 Account A1", "level": 3, "value_book": "$\xa01,400.00"},
            {"name": "XPS", "level": 4, "value_book": "$\xa01,400.00"},
            {
                "name": "Total 1110 Account A1",
                "level": 3,
                "value_book": "$\xa01,400.00",
            },
            {"name": "Total 11 Group 11", "level": 2, "value_book": "$\xa03,600.00"},
            {"name": "12 Group 12", "level": 2, "value_book": "$\xa01,600.00"},
            {"name": "1200 Account B", "level": 3, "value_book": "$\xa01,600.00"},
            {"name": "MacBook", "level": 4, "value_book": "$\xa01,600.00"},
            {"name": "Total 1200 Account B", "level": 3, "value_book": "$\xa01,600.00"},
            {"name": "Total 12 Group 12", "level": 2, "value_book": "$\xa01,600.00"},
            {"name": "1300 Account C", "level": 2, "value_book": "$\xa01,280.00"},
            {"name": "Aspire", "level": 3, "value_book": "$\xa01,280.00"},
            {"name": "Total 1300 Account C", "level": 2, "value_book": "$\xa01,280.00"},
            {"name": "1400 Account D", "level": 2, "value_book": "$\xa0440.00"},
            {"name": "Playstation", "level": 3, "value_book": "$\xa0440.00"},
            {"name": "Total 1400 Account D", "level": 2, "value_book": "$\xa0440.00"},
            {"name": "Total 1 Group 1", "level": 1, "value_book": "$\xa06,920.00"},
            {"name": "(No Group)", "level": 1, "value_book": "$\xa0400.00"},
            {"name": "9999 Account E", "level": 2, "value_book": "$\xa0400.00"},
            {"name": "Xbox", "level": 3, "value_book": "$\xa0400.00"},
            {"name": "Total 9999 Account E", "level": 2, "value_book": "$\xa0400.00"},
            {"name": "Total (No Group)", "level": 1, "value_book": "$\xa0400.00"},
            {"name": "Total", "level": 1, "value_book": "$\xa07,320.00"},
        ]

        self.assertEqual(len(lines), len(expected_values))
        self.assertEqual(lines, expected_values)

    def test_depreciation_schedule_disposal_move_unposted(self):
        asset = self.env["resource.asset"].create(
            {
                "name": "test asset",
                "depreciation_method": "linear",
                "value_original": 1000,
                "depreciation_duration": 5,
                "depreciation_period": "12",
                "date_acquisition": fields.Date.today()
                + relativedelta(years=-2, month=1, day=1),
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
            }
        )
        asset.action_confirm()

        expense_account_copy = self.company_data["default_account_expense"].copy()

        disposal_action_view = (
            self.env["asset.modify"]
            .create(
                {
                    "asset_id": asset.id,
                    "modify_action": "dispose",
                    "loss_account_id": expense_account_copy.id,
                    "date": fields.Date.today() + relativedelta(days=-1),
                }
            )
            .action_sell_dispose()
        )

        report = self.env.ref("account_depreciation.assets_report")
        options = self._generate_options(report, "2021-01-01", "2021-12-31")

        expected_values_asset_disposal_unposted = [
            ("test asset", 1000.0, 0.0, 0, 1000.0, 400.0, 100.0, 0.0, 500.0, 500.0),
        ]

        self.assertLinesValues(
            report._get_lines(options)[2:3],
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            expected_values_asset_disposal_unposted,
            options,
        )

        self.env["account.move"].browse(
            disposal_action_view.get("res_id")
        ).action_post()

        expected_values_asset_disposal_posted = [
            ("test asset", 1000.0, 0.0, 1000.0, 0.0, 400.0, 100.0, 500.0, 0.0, 0.0),
        ]

        self.assertLinesValues(
            report._get_lines(options)[2:3],
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            expected_values_asset_disposal_posted,
            options,
        )

    def test_depreciation_schedule_disposal_move_unposted_with_non_depreciable_value(
        self,
    ):
        asset = self.env["resource.asset"].create(
            {
                "name": "test asset",
                "depreciation_method": "linear",
                "value_original": 10000,
                "value_salvage": 8000,
                "depreciation_duration": 24,
                "depreciation_period": "1",
                "date_acquisition": fields.Date.today()
                + relativedelta(months=-1, day=1),
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
            }
        )
        asset.action_confirm()

        report = self.env.ref("account_depreciation.assets_report")

        options = self._generate_options(report, "2021-07-01", "2021-07-31")

        expected_values_asset_disposal_unposted = [
            ("test asset", 10000.0, 0.0, 0.0, 10000.0, 83.33, 0.0, 0.0, 83.33, 9916.67),
        ]

        self.assertLinesValues(
            report._get_lines(options)[2:3],
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            expected_values_asset_disposal_unposted,
            options,
        )

        expense_account_copy = self.company_data["default_account_expense"].copy()

        disposal_action_view = (
            self.env["asset.modify"]
            .create(
                {
                    "asset_id": asset.id,
                    "modify_action": "dispose",
                    "loss_account_id": expense_account_copy.id,
                    "date": fields.Date.today(),
                }
            )
            .action_sell_dispose()
        )

        expected_values_asset_disposal_unposted = [
            (
                "test asset",
                10000.0,
                0.0,
                0.0,
                10000.0,
                83.33,
                2.69,
                0.0,
                86.02,
                9913.98,
            ),
        ]

        self.assertLinesValues(
            report._get_lines(options)[2:3],
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            expected_values_asset_disposal_unposted,
            options,
        )

        self.env["account.move"].browse(disposal_action_view["res_id"]).action_post()

        expected_values_asset_disposal_posted = [
            ("test asset", 10000.0, 0.0, 10000.0, 0.0, 83.33, 2.69, 86.02, 0.0, 0.0),
        ]

        self.assertLinesValues(
            report._get_lines(options)[2:3],
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            expected_values_asset_disposal_posted,
            options,
        )

    def test_asset_analytic_on_lines(self):
        CEO_car = self.env["resource.asset"].create(
            {
                "value_salvage": 2000.0,
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "CEO's Car",
                "value_original": 12000.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
                "date_acquisition": "2020-01-01",
            }
        )
        CEO_car._onchange_depreciation_profile_id()
        CEO_car.depreciation_duration = 5
        CEO_car.analytic_distribution = {self.analytic_account.id: 100}

        CEO_car.action_confirm()

        for move in CEO_car.depreciation_move_ids:
            self.assertRecordValues(
                move.line_ids,
                [
                    {
                        "analytic_distribution": {str(self.analytic_account.id): 100},
                    },
                    {
                        "analytic_distribution": {str(self.analytic_account.id): 100},
                    },
                ],
            )

        CEO_car.analytic_distribution = {str(self.analytic_account.id): 200}

        for move in CEO_car.depreciation_move_ids.filtered(
            lambda m: m.state == "posted"
        ):
            self.assertRecordValues(
                move.line_ids,
                [
                    {
                        "analytic_distribution": {str(self.analytic_account.id): 100},
                    },
                    {
                        "analytic_distribution": {str(self.analytic_account.id): 100},
                    },
                ],
            )

        for move in CEO_car.depreciation_move_ids.filtered(
            lambda m: m.state == "draft"
        ):
            self.assertRecordValues(
                move.line_ids,
                [
                    {
                        "analytic_distribution": {str(self.analytic_account.id): 200},
                    },
                    {
                        "analytic_distribution": {str(self.analytic_account.id): 200},
                    },
                ],
            )

    def test_asset_analytic_filter(self):
        truck_b = self.truck.copy()
        truck_b.date_acquisition = self.truck.date_acquisition
        truck_b.action_confirm()
        self.truck.analytic_distribution = {self.analytic_account.id: 100}

        with self.enter_registry_test_mode():
            self.env.ref(
                "account.ir_cron_auto_post_draft_entry"
            ).method_direct_trigger()

        self.env.company.totals_below_sections = False
        report = self.env.ref("account_depreciation.assets_report")

        options = self._generate_options(
            report,
            "2021-01-01",
            "2021-12-31",
            default_options={"assets_grouping_field": "none", "unfold_all": False},
        )

        self.assertLinesValues(
            report._get_lines(options),
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "truck",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "truck (copy)",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "Total",
                    20000,
                    0,
                    0,
                    20000,
                    9000,
                    0,
                    0,
                    9000,
                    11000,
                ),
            ],
            options,
        )
        options["analytic_accounts"] = [self.analytic_account.id]
        self.assertLinesValues(
            report._get_lines(options),
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "truck",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "Total",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
            ],
            options,
        )

    def test_asset_analytic_groupby(self):
        truck_b = self.truck.copy()
        truck_b.date_acquisition = self.truck.date_acquisition
        truck_b.action_confirm()
        self.truck.analytic_distribution = {self.analytic_account.id: 100}
        with self.enter_registry_test_mode():
            self.env.ref(
                "account.ir_cron_auto_post_draft_entry"
            ).method_direct_trigger()

        self.env.company.totals_below_sections = False
        report = self.env.ref("account_depreciation.assets_report")
        report.filter_analytic_groupby = True

        options = self._generate_options(
            report,
            "2021-01-01",
            "2021-12-31",
            default_options={"assets_grouping_field": "none", "unfold_all": False},
        )

        self.assertLinesValues(
            report._get_lines(options),
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "truck",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "truck (copy)",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "Total",
                    20000,
                    0,
                    0,
                    20000,
                    9000,
                    0,
                    0,
                    9000,
                    11000,
                ),
            ],
            options,
        )
        options = self._generate_options(
            report,
            "2021-01-01",
            "2021-12-31",
            default_options={
                "assets_grouping_field": "none",
                "unfold_all": False,
                "analytic_accounts_groupby": [self.analytic_account.id],
            },
        )
        self.assertLinesValues(
            report._get_lines(options),
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 17, 18, 19, 20, 21, 22, 23, 24],
            [
                (
                    "truck",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "truck (copy)",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "Total",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                    20000,
                    0,
                    0,
                    20000,
                    9000,
                    0,
                    0,
                    9000,
                    11000,
                ),
            ],
            options,
        )

    def test_asset_modify_sell_multicurrency(self):
        closing_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "currency_id": self.other_currency.id,
                "invoice_line_ids": [Command.create({"price_unit": 5000})],
            }
        )
        self.env["asset.modify"].create(
            {
                "asset_id": self.truck.id,
                "invoice_line_ids": closing_invoice.invoice_line_ids,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "modify_action": "sell",
            }
        ).action_sell_dispose()

        closing_move = self.truck.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )

        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "debit": 0,
                    "credit": 10000,
                    "account_id": self.truck.account_asset_id.id,
                },
                {
                    "debit": 4500,
                    "credit": 0,
                    "account_id": self.truck.account_depreciation_id.id,
                },
                {
                    "debit": 2500,
                    "credit": 0,
                    "account_id": closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "debit": 3000,
                    "credit": 0,
                    "account_id": self.env.company.loss_account_id.id,
                },
            ],
        )

    def test_depreciation_schedule_prefix_groups(self):
        asset_group = self.env["account.asset.group"].create({"name": "Odoo Office"})
        for i in range(1, 3):
            asset = self.env["resource.asset"].create(
                {
                    "depreciation_period": "12",
                    "depreciation_duration": 4,
                    "name": f"Asset {i}",
                    "value_original": i * 100.0,
                    "date_acquisition": fields.Date.today() - relativedelta(years=3),
                    "account_asset_id": self.company_data["default_account_assets"].id,
                    "asset_group_id": asset_group.id,
                    "account_depreciation_id": self.company_data[
                        "default_account_assets"
                    ]
                    .copy()
                    .id,
                    "account_depreciation_expense_id": self.company_data[
                        "default_account_expense"
                    ].id,
                    "depreciation_journal_id": self.company_data[
                        "default_journal_misc"
                    ].id,
                    "depreciation_prorata": "none",
                }
            )
            asset.action_confirm()

        with self.enter_registry_test_mode():
            self.env.ref(
                "account.ir_cron_auto_post_draft_entry"
            ).method_direct_trigger()

        self.env.company.totals_below_sections = False
        report = self.env.ref("account_depreciation.assets_report")

        options = self._generate_options(
            report,
            "2021-01-01",
            "2021-12-31",
            default_options={"assets_grouping_field": "none"},
        )
        self.assertLinesValues(
            report._get_lines(options),
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "truck",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "Asset 1",
                    100,
                    0,
                    0,
                    100,
                    75,
                    0,
                    0,
                    75,
                    25,
                ),
                (
                    "Asset 2",
                    200,
                    0,
                    0,
                    200,
                    150,
                    0,
                    0,
                    150,
                    50,
                ),
                (
                    "Total",
                    10300,
                    0,
                    0,
                    10300,
                    4725,
                    0,
                    0,
                    4725,
                    5575,
                ),
            ],
            options,
        )

        options = self._generate_options(
            report,
            "2021-01-01",
            "2021-12-31",
            default_options={"assets_grouping_field": "account_id"},
        )
        options["unfold_all"] = True
        self.assertLinesValues(
            report._get_lines(options),
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "151000 Fixed Asset",
                    10300,
                    0,
                    0,
                    10300,
                    4725,
                    0,
                    0,
                    4725,
                    5575,
                ),
                (
                    "truck",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "Asset 1",
                    100,
                    0,
                    0,
                    100,
                    75,
                    0,
                    0,
                    75,
                    25,
                ),
                (
                    "Asset 2",
                    200,
                    0,
                    0,
                    200,
                    150,
                    0,
                    0,
                    150,
                    50,
                ),
                (
                    "Total",
                    10300,
                    0,
                    0,
                    10300,
                    4725,
                    0,
                    0,
                    4725,
                    5575,
                ),
            ],
            options,
        )

        report.prefix_groups_threshold = 3
        options = self._generate_options(
            report,
            "2021-01-01",
            "2021-12-31",
            default_options={"assets_grouping_field": "none", "unfold_all": True},
        )
        options["unfold_all"] = True
        self.assertLinesValues(
            report._get_lines(options),
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "A (2 lines)",
                    300,
                    0,
                    0,
                    300,
                    225,
                    0,
                    0,
                    225,
                    75,
                ),
                (
                    "Asset 1",
                    100,
                    0,
                    0,
                    100,
                    75,
                    0,
                    0,
                    75,
                    25,
                ),
                (
                    "Asset 2",
                    200,
                    0,
                    0,
                    200,
                    150,
                    0,
                    0,
                    150,
                    50,
                ),
                (
                    "T (1 line)",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "truck",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "Total",
                    10300,
                    0,
                    0,
                    10300,
                    4725,
                    0,
                    0,
                    4725,
                    5575,
                ),
            ],
            options,
        )

        options = self._generate_options(
            report,
            "2021-01-01",
            "2021-12-31",
            default_options={"assets_grouping_field": "account_id", "unfold_all": True},
        )
        options["unfold_all"] = True
        self.assertLinesValues(
            report._get_lines(options),
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "151000 Fixed Asset",
                    10300,
                    0,
                    0,
                    10300,
                    4725,
                    0,
                    0,
                    4725,
                    5575,
                ),
                (
                    "A (2 lines)",
                    300,
                    0,
                    0,
                    300,
                    225,
                    0,
                    0,
                    225,
                    75,
                ),
                (
                    "Asset 1",
                    100,
                    0,
                    0,
                    100,
                    75,
                    0,
                    0,
                    75,
                    25,
                ),
                (
                    "Asset 2",
                    200,
                    0,
                    0,
                    200,
                    150,
                    0,
                    0,
                    150,
                    50,
                ),
                (
                    "T (1 line)",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "truck",
                    10000,
                    0,
                    0,
                    10000,
                    4500,
                    0,
                    0,
                    4500,
                    5500,
                ),
                (
                    "Total",
                    10300,
                    0,
                    0,
                    10300,
                    4725,
                    0,
                    0,
                    4725,
                    5575,
                ),
            ],
            options,
        )

        options = self._generate_options(
            report,
            "2021-01-01",
            "2021-12-31",
            default_options={"assets_grouping_field": "asset_group_id"},
        )
        options["unfold_all"] = True
        self.assertLinesValues(
            report._get_lines(options),
            [0, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                ("Odoo Office", 300, 0, 0, 300, 225, 0, 0, 225, 75),
                ("Asset 1", 100, 0, 0, 100, 75, 0, 0, 75, 25),
                ("Asset 2", 200, 0, 0, 200, 150, 0, 0, 150, 50),
                ("(No Asset Group)", 10000, 0, 0, 10000, 4500, 0, 0, 4500, 5500),
                ("truck", 10000, 0, 0, 10000, 4500, 0, 0, 4500, 5500),
                ("Total", 10300, 0, 0, 10300, 4725, 0, 0, 4725, 5575),
            ],
            options,
        )

    def test_depreciation_schedule_prefix_groups_with_comparison(self):
        for i in range(1, 3):
            asset = self.env["resource.asset"].create(
                {
                    "depreciation_period": "12",
                    "depreciation_duration": 4,
                    "name": f"Bldg {i}",
                    "value_original": i * 100.0,
                    "date_acquisition": fields.Date.from_string("2021-06-01"),
                    "account_asset_id": self.company_data["default_account_assets"].id,
                    "account_depreciation_id": self.company_data[
                        "default_account_assets"
                    ]
                    .copy()
                    .id,
                    "account_depreciation_expense_id": self.company_data[
                        "default_account_expense"
                    ].id,
                    "depreciation_journal_id": self.company_data[
                        "default_journal_misc"
                    ].id,
                    "depreciation_prorata": "none",
                }
            )
            asset.action_confirm()
        self.env["account.move"].search(
            [
                ("state", "=", "draft"),
                ("auto_post", "!=", "no"),
                ("date", "<=", fields.Date.context_today(self.env["account.move"])),
            ]
        )._post()

        report = self.env.ref("account_depreciation.assets_report")
        report.prefix_groups_threshold = 2
        report.filter_period_comparison = True
        options = self._generate_options(
            report,
            "2021-01-01",
            "2021-12-31",
            default_options={"assets_grouping_field": "none", "unfold_all": True},
        )
        options = self._update_comparison_filter(options, report, "previous_period", 1)

        lines = report._get_lines(options)

        prefix_line_names = [
            line["name"] for line in lines if line["name"].startswith("B ")
        ]
        self.assertEqual(prefix_line_names, ["B (2 lines)"])

    def test_archive_asset_model(self):
        self.account_asset_model_fixedassets.active = False
        self.assertFalse(self.account_asset_model_fixedassets.active)

    def test_asset_increase_with_lock_year(self):
        self.company_data["company"].fiscalyear_lock_date = fields.Date.to_date(
            "2021-03-01"
        )

        asset = self.env["resource.asset"].create(
            {
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data["default_account_assets"]
                .copy()
                .id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "name": "Car",
                "date_acquisition": fields.Date.today() + relativedelta(months=-6),
                "value_original": 12000,
                "depreciation_duration": 12,
                "depreciation_period": "1",
                "depreciation_method": "linear",
            }
        )

        asset.action_confirm()

        self.assertRecordValues(
            asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)),
            [
                {"date": fields.Date.to_date("2021-03-31")},
                {"date": fields.Date.to_date("2021-03-31")},
                {"date": fields.Date.to_date("2021-03-31")},
                {"date": fields.Date.to_date("2021-04-30")},
                {"date": fields.Date.to_date("2021-05-31")},
                {"date": fields.Date.to_date("2021-06-30")},
                {"date": fields.Date.to_date("2021-07-31")},
                {"date": fields.Date.to_date("2021-08-31")},
                {"date": fields.Date.to_date("2021-09-30")},
                {"date": fields.Date.to_date("2021-10-31")},
                {"date": fields.Date.to_date("2021-11-30")},
                {"date": fields.Date.to_date("2021-12-31")},
            ],
        )

        self.assertEqual(asset.value_book, 6000)

        self.env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "name": "Test increase with lock date",
                "value_depreciable_residual": 8000.0,
                "date": fields.Date.today() + relativedelta(days=-1),
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()

        self.assertEqual(asset.value_book, 8000)

        self.assertRecordValues(
            asset.increase_ids.depreciation_move_ids.sorted(
                lambda dep: (dep.date, dep.id)
            ),
            [
                {
                    "date": fields.Date.to_date("2021-07-31"),
                    "depreciation_value": 333.33,
                },
                {
                    "date": fields.Date.to_date("2021-08-31"),
                    "depreciation_value": 333.34,
                },
                {
                    "date": fields.Date.to_date("2021-09-30"),
                    "depreciation_value": 333.33,
                },
                {
                    "date": fields.Date.to_date("2021-10-31"),
                    "depreciation_value": 333.33,
                },
                {
                    "date": fields.Date.to_date("2021-11-30"),
                    "depreciation_value": 333.34,
                },
                {
                    "date": fields.Date.to_date("2021-12-31"),
                    "depreciation_value": 333.33,
                },
            ],
        )

    def test_asset_decrease_with_lock_year(self):
        self.company_data["company"].fiscalyear_lock_date = fields.Date.to_date(
            "2021-03-01"
        )

        asset = self.env["resource.asset"].create(
            {
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data["default_account_assets"]
                .copy()
                .id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "name": "Car",
                "date_acquisition": fields.Date.today() + relativedelta(months=-6),
                "value_original": 12000,
                "depreciation_duration": 12,
                "depreciation_period": "1",
                "depreciation_method": "linear",
            }
        )

        asset.action_confirm()

        self.assertEqual(asset.value_book, 6000)

        self.env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "name": "Test decrease with lock date",
                "value_depreciable_residual": 4000.0,
                "date": fields.Date.today() + relativedelta(days=-1),
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()

        self.assertEqual(asset.value_book, 4000)

        self.assertRecordValues(
            asset.depreciation_move_ids.sorted(lambda dep: (dep.date, dep.id)),
            [
                {"date": fields.Date.to_date("2021-03-31"), "depreciation_value": 1000},
                {"date": fields.Date.to_date("2021-03-31"), "depreciation_value": 1000},
                {"date": fields.Date.to_date("2021-03-31"), "depreciation_value": 1000},
                {"date": fields.Date.to_date("2021-04-30"), "depreciation_value": 1000},
                {"date": fields.Date.to_date("2021-05-31"), "depreciation_value": 1000},
                {"date": fields.Date.to_date("2021-06-30"), "depreciation_value": 1000},
                {"date": fields.Date.to_date("2021-06-30"), "depreciation_value": 2000},
                {
                    "date": fields.Date.to_date("2021-07-31"),
                    "depreciation_value": 666.67,
                },
                {
                    "date": fields.Date.to_date("2021-08-31"),
                    "depreciation_value": 666.66,
                },
                {
                    "date": fields.Date.to_date("2021-09-30"),
                    "depreciation_value": 666.67,
                },
                {
                    "date": fields.Date.to_date("2021-10-31"),
                    "depreciation_value": 666.67,
                },
                {
                    "date": fields.Date.to_date("2021-11-30"),
                    "depreciation_value": 666.66,
                },
                {
                    "date": fields.Date.to_date("2021-12-31"),
                    "depreciation_value": 666.67,
                },
            ],
        )

    def test_asset_onchange_model(self):
        account_asset = self.company_data["default_account_assets"].copy()
        asset_model = self.env["account.depreciation.profile"].create(
            {
                "name": "test model",
                "active": True,
                "depreciation_method": "linear",
                "depreciation_duration": 5,
                "depreciation_period": "1",
                "depreciation_prorata": "none",
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "account_asset_id": account_asset.id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
            }
        )

        asset_model_with_account = self.env["account.depreciation.profile"].create(
            {
                "name": "test model with account",
                "active": True,
                "depreciation_method": "linear",
                "depreciation_duration": 5,
                "depreciation_period": "1",
                "depreciation_prorata": "none",
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
            }
        )

        asset_form = Form(
            self.env["resource.asset"].with_context(default_depreciation_state="draft"),
            view="account_depreciation.view_account_asset_form",
        )
        asset_form.name = "Test Asset"
        asset_form.value_original = 10000
        asset_form.depreciation_profile_id = asset_model

        self.assertEqual(
            asset_form.account_asset_id,
            account_asset,
            "The account_asset_id should be the one from the model",
        )

        asset_form.depreciation_profile_id = asset_model_with_account
        self.assertEqual(
            asset_form.account_asset_id,
            self.company_data["default_account_assets"],
            "The account_asset_id should be computed from the depreciation account from the model",
        )

        other_account_on_bill = self.company_data["default_account_assets"].copy()
        other_account_on_bill.create_asset = "draft"
        other_account_on_bill.depreciation_profile_ids = asset_model
        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "invoice_date": "2020-12-31",
                "partner_id": self.partner_a.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "A beautiful small bomb",
                            "account_id": other_account_on_bill.id,
                            "price_unit": 200.0,
                            "quantity": 1,
                        },
                    ),
                ],
            }
        )
        invoice.action_post()

        self.assertEqual(
            invoice.capitalised_asset_ids.account_asset_id,
            other_account_on_bill,
            "The account should be the one from the bill, not the model",
        )

        asset_form = Form(
            invoice.capitalised_asset_ids,
            view="account_depreciation.view_account_asset_form",
        )
        asset_form.depreciation_profile_id = asset_model

        self.assertEqual(
            asset_form.account_asset_id,
            other_account_on_bill,
            "We keep the account from the bill",
        )

    def test_asset_reevaluation_degressive_linear(self):
        asset = self.env["resource.asset"].create(
            {
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "Car with purple sticker",
                "value_original": 10000.0,
                "date_acquisition": fields.Date.today() - relativedelta(years=2),
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data["default_account_assets"]
                .copy()
                .id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "depreciation_prorata": "none",
                "depreciation_method": "degressive_then_linear",
                "depreciation_factor": 0.4,
            }
        )
        asset.action_confirm()
        self.assertRecordValues(
            asset.depreciation_move_ids._sorted_by_date(),
            [
                {
                    "depreciation_value": 4000,
                    "asset_remaining_value": 6000,
                    "state": "posted",
                },
                {
                    "depreciation_value": 2400,
                    "asset_remaining_value": 3600,
                    "state": "posted",
                },
                {
                    "depreciation_value": 2000,
                    "asset_remaining_value": 1600,
                    "state": "draft",
                },
                {
                    "depreciation_value": 1600,
                    "asset_remaining_value": 0,
                    "state": "draft",
                },
            ],
        )
        self.env["asset.modify"].create(
            {
                "name": "Inflation made it take 20%!",
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "asset_id": asset.id,
                "value_depreciable_residual": 5600,
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()
        self.assertRecordValues(
            asset.increase_ids[0].depreciation_move_ids.sorted(
                lambda mv: (mv.date, mv.id)
            ),
            [
                {
                    "depreciation_value": 1111.11,
                    "asset_remaining_value": 888.89,
                    "state": "draft",
                },
                {
                    "depreciation_value": 888.89,
                    "asset_remaining_value": 0,
                    "state": "draft",
                },
            ],
        )

    def test_asset_move_type(self):
        asset_account_id = self.company_data["default_account_assets"].id

        bill = self.env["account.move"].create(
            [
                {
                    "move_type": "in_invoice",
                    "invoice_date": fields.Date.today()
                    + relativedelta(months=-6, days=-1),
                    "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Truck",
                                "account_id": asset_account_id,
                                "quantity": 1.0,
                                "price_unit": 1000.0,
                                "tax_ids": [
                                    Command.set(
                                        self.company_data["default_tax_sale"].ids
                                    )
                                ],
                            }
                        )
                    ],
                },
            ]
        )
        bill.action_post()
        asset_line = bill.line_ids.filtered(
            lambda x: x.account_id.id == asset_account_id
        )
        asset_form = Form(
            self.env["resource.asset"].with_context(
                default_depreciation_state="draft",
                default_original_move_line_ids=asset_line.ids,
            ),
            view="account_depreciation.view_account_asset_form",
        )
        asset_form.original_move_line_ids = asset_line
        asset_form.account_depreciation_expense_id = self.company_data[
            "default_account_expense"
        ]
        car = asset_form.save()
        car.action_confirm()

        self.assertTrue(
            all(
                car.depreciation_move_ids.mapped(
                    lambda m: m.asset_move_type == "depreciation"
                )
            )
        )

        self.env["asset.modify"].create(
            {
                "name": "Little scratch :(",
                "asset_id": car.id,
                "value_depreciable_residual": car.value_book - 150,
                "date": fields.Date.today(),
            }
        ).action_modify()

        added_move_on_revaluation = car.depreciation_move_ids.filtered(
            lambda m: m.date == fields.Date.today()
        )
        self.assertRecordValues(
            added_move_on_revaluation.sorted(lambda mv: mv.id),
            [
                {"asset_move_type": "depreciation"},
                {"asset_move_type": "negative_revaluation"},
            ],
        )

        closing_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create({"price_unit": car.value_book + 100})
                ],
            }
        )

        self.env["asset.modify"].create(
            {
                "asset_id": car.id,
                "modify_action": "sell",
                "invoice_line_ids": closing_invoice.invoice_line_ids,
                "date": fields.Date.today(),
            }
        ).action_sell_dispose()
        selling_move = car.depreciation_move_ids.filtered(lambda l: l.state == "draft")
        selling_move.action_post()

        added_move_on_sale = (
            car.depreciation_move_ids.filtered(lambda m: m.date == fields.Date.today())
            - added_move_on_revaluation
        )
        self.assertTrue(added_move_on_sale.asset_move_type == "sale")
        self.assertEqual(car.value_gain_on_sale, 100)

        new_car = car.copy()
        new_car.action_confirm()

        self.env["asset.modify"].create(
            {
                "name": "New beautiful sticker :D",
                "asset_id": new_car.id,
                "value_depreciable_residual": new_car.value_book + 50,
                "value_salvage": 0,
                "date": fields.Date.today(),
                "account_asset_counterpart_id": self.assert_counterpart_account_id,
            }
        ).action_modify()

        self.assertEqual(
            new_car.increase_ids.original_move_line_ids.move_id.asset_move_type,
            "positive_revaluation",
            "the original move of the child asset is set as 'positive_revaluation'",
        )

        disposal_action_view = (
            self.env["asset.modify"]
            .create(
                {
                    "asset_id": new_car.id,
                    "modify_action": "dispose",
                    "date": fields.Date.today(),
                }
            )
            .action_sell_dispose()
        )

        self.env["account.move"].browse(disposal_action_view["res_id"]).action_post()
        self.assertEqual(
            self.env["account.move"]
            .browse(disposal_action_view["res_id"])
            .asset_move_type,
            "disposal",
        )

    def test_asset_already_depreciated(self):
        asset = self.env["resource.asset"].create(
            {
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "Car with purple sticker",
                "value_original": 10000.0,
                "date_acquisition": fields.Date.today() - relativedelta(years=1),
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data["default_account_assets"]
                .copy()
                .id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "depreciation_prorata": "none",
                "value_depreciated_import": 3000,
            }
        )
        asset.action_confirm()

        self.env["asset.modify"].create(
            {
                "asset_id": asset.id,
                "date": fields.Date.today() - relativedelta(days=1),
                "name": "Test reason",
            }
        ).action_modify()

        self.assertRecordValues(
            asset.depreciation_move_ids._sorted_by_date(),
            [
                {
                    "depreciation_value": 1000,
                    "date": fields.Date.to_date("2021-12-31"),
                },
                {
                    "depreciation_value": 2000,
                    "date": fields.Date.to_date("2022-12-31"),
                },
                {
                    "depreciation_value": 2000,
                    "date": fields.Date.to_date("2023-12-31"),
                },
                {
                    "depreciation_value": 2000,
                    "date": fields.Date.to_date("2024-12-31"),
                },
            ],
        )

        fully_depreciated_asset = self.env["resource.asset"].create(
            {
                "depreciation_period": "12",
                "depreciation_duration": 5,
                "name": "Car with purple sticker",
                "value_original": 10000.0,
                "date_acquisition": fields.Date.today() - relativedelta(years=2),
                "account_asset_id": self.company_data["default_account_assets"].id,
                "account_depreciation_id": self.company_data["default_account_assets"]
                .copy()
                .id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "depreciation_prorata": "none",
                "value_salvage": 4000,
                "value_depreciated_import": 6000,
            }
        )
        fully_depreciated_asset.action_confirm()

        self.env["asset.modify"].create(
            {
                "asset_id": fully_depreciated_asset.id,
                "date": fields.Date.today(),
                "modify_action": "dispose",
            }
        ).action_sell_dispose()
        self.assertEqual(
            len(fully_depreciated_asset.depreciation_move_ids),
            1,
            "Only the disposal should be created",
        )

    def test_asset_acquisition_date_from_bill(self):
        self.company_data["default_account_assets"].create_asset = "draft"
        self.company_data[
            "default_account_assets"
        ].depreciation_profile_ids = self.account_asset_model_fixedassets

        bill = (
            self.env["account.move"]
            .with_context(asset_type="purchase")
            .create(
                {
                    "move_type": "in_invoice",
                    "partner_id": self.partner_a.id,
                    "date": "2020-06-15",
                    "invoice_date": "2020-06-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Insurance claim",
                                "account_id": self.company_data[
                                    "default_account_assets"
                                ].id,
                                "price_unit": 450,
                                "quantity": 1,
                            }
                        )
                    ],
                }
            )
        )
        bill.action_post()
        asset = bill.capitalised_asset_ids
        self.assertEqual(asset.date_acquisition, bill.invoice_date)

    def test_asset_write_multi_company(self):
        assets = (
            self.env["resource.asset"]
            .with_context(default_depreciation_state="draft")
            .create(
                [
                    {
                        "company_id": company_data["company"].id,
                        "name": "test asset",
                    }
                    for company_data in [self.company_data, self.company_data_2]
                ]
            )
        )
        self.assertEqual(assets[0].company_id, self.company_data["company"])
        self.assertEqual(assets[1].company_id, self.company_data_2["company"])
        assets.action_confirm()

    def test_depreciation_moves_company_with_sub_company(self):
        company = self.env.company
        branch_x = self.env["res.company"].create(
            {
                "name": "Branch X",
                "country_id": company.country_id.id,
                "parent_id": company.id,
            }
        )

        asset_vals = {
            "depreciation_period": "12",
            "depreciation_duration": 5,
            "name": "Car with purple sticker",
            "value_original": 10000.0,
            "date_acquisition": fields.Date.today() - relativedelta(years=1),
            "account_asset_id": self.company_data["default_account_assets"].id,
            "account_depreciation_id": self.company_data["default_account_assets"]
            .copy()
            .id,
            "account_depreciation_expense_id": self.company_data[
                "default_account_expense"
            ].id,
            "depreciation_journal_id": self.company_data["default_journal_misc"].id,
        }

        setup_list = [
            {"company_ids": (company + branch_x).ids, "company_id": branch_x.id},
            {"company_ids": branch_x.ids, "company_id": branch_x.id},
            {"company_ids": (company + branch_x).ids, "company_id": company.id},
            {"company_ids": company.ids, "company_id": company.id},
        ]

        expected_vals_list = [branch_x, branch_x, company, company]

        for setup, expected in zip(setup_list, expected_vals_list, strict=False):
            with self.subTest(setup=setup, expected_company=expected):
                self.env.user.write(
                    {
                        "company_ids": [Command.set(setup["company_ids"])],
                        "company_id": setup["company_id"],
                    }
                )
                asset = self.env["resource.asset"].create(asset_vals)
                asset._create_depreciation_entries()
                self.assertEqual(
                    asset.depreciation_move_ids.mapped("company_id"), expected
                )

    def test_multiple_asset_models_with_branches(self):

        branch_a = self.setup_other_company(
            name="Test Branch A", parent_id=self.company_data["company"].id
        )
        asset_model_a = self.account_asset_model_fixedassets.copy()
        asset_model_a.company_id = branch_a["company"]

        branch_b = self.setup_other_company(
            name="Test Branch B", parent_id=self.company_data["company"].id
        )
        asset_model_b = self.account_asset_model_fixedassets.copy()
        asset_model_b.company_id = branch_b["company"]

        self.company_data["default_account_assets"].sudo().depreciation_profile_ids = (
            asset_model_a + asset_model_b
        )
        self.company_data["default_account_assets"].create_asset = "draft"

        vendor_bill = (
            self.env["account.move"]
            .with_company(branch_a["company"])
            .create(
                {
                    "move_type": "in_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_date": fields.Date.today(),
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Very little red car",
                                "account_id": self.company_data[
                                    "default_account_assets"
                                ].id,
                                "price_unit": 1000,
                                "quantity": 1,
                            }
                        )
                    ],
                }
            )
        )
        vendor_bill.action_post()

        self.assertEqual(
            len(vendor_bill.capitalised_asset_ids),
            1,
            "Only one asset should have been created.",
        )
        self.assertEqual(
            vendor_bill.capitalised_asset_ids.company_id,
            branch_a["company"],
            f"The asset should have been created on company: {branch_a['company'].name}",
        )

    def test_account_asset_lock_cancel_storno(self):
        self.env.company.account_storno = True
        today = fields.Date.today()

        locked_car = self.env["resource.asset"].create(
            {
                "value_salvage": 2000.0,
                "depreciation_period": "12",
                "depreciation_duration": 10,
                "name": "Locked Car",
                "value_original": 14000.0,
                "depreciation_profile_id": self.account_asset_model_fixedassets.id,
                "date_acquisition": today + relativedelta(years=-3, month=1, day=1),
            }
        )
        locked_car._onchange_depreciation_profile_id()
        locked_car.action_confirm()

        locked_car.company_id.fiscalyear_lock_date = today + relativedelta(years=-1)

        self.assertEqual(len(locked_car.depreciation_move_ids), 3)
        locked_car.action_cancel()
        self.assertRecordValues(
            locked_car,
            [
                {
                    "depreciation_state": "cancelled",
                    "value_book": 14000.0,
                    "value_depreciable_residual": 12000,
                    "value_salvage": 2000,
                }
            ],
        )

        self.assertEqual(len(locked_car.depreciation_move_ids), 4)
        self.assertEqual(
            len(
                locked_car.depreciation_move_ids.filtered(
                    lambda m: m.date >= locked_car.company_id.fiscalyear_lock_date
                )
            ),
            2,
            "Two moves after the lock date",
        )

        for depreciation in locked_car.depreciation_move_ids:
            self.assertTrue(
                depreciation.reversal_move_ids or depreciation.reversed_entry_id
            )
            if depreciation.date >= locked_car.company_id.fiscalyear_lock_date:
                self.assertEqual(
                    len(depreciation.line_ids), 2, "Reversal move should have 2 lines"
                )
                self.assertRecordValues(
                    depreciation.line_ids,
                    [
                        {
                            "debit": 0.0,
                            "credit": -4000.00,
                            "account_id": locked_car.account_depreciation_id.id,
                        },
                        {
                            "debit": -4000.00,
                            "credit": 0.0,
                            "account_id": locked_car.account_depreciation_expense_id.id,
                        },
                    ],
                )

    def test_asset_modify_sell_profit_storno(self):
        self.env.company.account_storno = True

        closing_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create({"price_unit": self.truck.value_book + 100})
                ],
            }
        )
        self.env["asset.modify"].create(
            {
                "asset_id": self.truck.id,
                "invoice_line_ids": closing_invoice.invoice_line_ids,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "modify_action": "sell",
            }
        ).action_sell_dispose()
        closing_move = self.truck.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )

        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "ref": "truck: Sale",
                    "debit": -10000.0,
                    "credit": 0.0,
                    "account_id": self.truck.account_asset_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 0.0,
                    "credit": -4500.0,
                    "account_id": self.truck.account_depreciation_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 0.0,
                    "credit": -5600.0,
                    "account_id": closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 0.0,
                    "credit": 100.0,
                    "account_id": self.env.company.gain_account_id.id,
                },
            ],
        )

    def test_asset_modify_sell_loss_storno(self):
        self.env.company.account_storno = True

        closing_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create({"price_unit": self.truck.value_book - 100})
                ],
            }
        )
        self.env["asset.modify"].create(
            {
                "asset_id": self.truck.id,
                "invoice_line_ids": closing_invoice.invoice_line_ids,
                "date": fields.Date.today() + relativedelta(months=-6, days=-1),
                "modify_action": "sell",
            }
        ).action_sell_dispose()
        closing_move = self.truck.depreciation_move_ids.filtered(
            lambda l: l.state == "draft"
        )

        self.assertRecordValues(
            closing_move.line_ids,
            [
                {
                    "ref": "truck: Sale",
                    "debit": -10000.0,
                    "credit": 0.0,
                    "account_id": self.truck.account_asset_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 0.0,
                    "credit": -4500.0,
                    "account_id": self.truck.account_depreciation_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 0.0,
                    "credit": -5400.0,
                    "account_id": closing_invoice.invoice_line_ids.account_id.id,
                },
                {
                    "ref": "truck: Sale",
                    "debit": 100.0,
                    "credit": 0.0,
                    "account_id": self.env.company.loss_account_id.id,
                },
            ],
        )

    def test_non_fully_deductible_asset(self):
        non_deductible_tax = self.env["account.tax"].create(
            {
                "name": "Non-deductible Tax",
                "amount": 21,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 10,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 90,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 10,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 90,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                ],
            }
        )
        account_asset_model = self.env["account.depreciation.profile"].create(
            {
                "account_depreciation_id": self.company_data[
                    "default_account_assets"
                ].id,
                "account_depreciation_expense_id": self.company_data[
                    "default_account_expense"
                ].id,
                "depreciation_journal_id": self.company_data["default_journal_misc"].id,
                "name": "Electronic devices",
                "depreciation_duration": 3,
                "depreciation_period": "12",
                "depreciation_prorata": "daily_computation",
            }
        )
        self.company_data["default_account_assets"].create_asset = "validate"
        self.company_data[
            "default_account_assets"
        ].depreciation_profile_ids = account_asset_model

        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.env["res.partner"]
                .create({"name": "Res Partner 12"})
                .id,
                "invoice_date": "2020-12-31",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Beautiful shiny smartphone",
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "price_unit": 1000,
                            "quantity": 1,
                            "deductible_amount": 20,
                            "tax_ids": non_deductible_tax.ids,
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        self.assertEqual(invoice.capitalised_asset_ids.value_original, 204.2)

    def test_non_deductible_tax_value_empty_ids(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
            }
        )
        with Form(move) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product_a
                line_form.tax_ids.clear()
                line_form.tax_ids.add(self.tax_armageddon)
