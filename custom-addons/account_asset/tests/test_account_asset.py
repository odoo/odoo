# -*- coding: utf-8 -*-

import time

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from odoo import fields, Command
from odoo.exceptions import UserError, MissingError
from odoo.tests.common import Form, tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@freeze_time('2021-07-01')
@tagged('post_install', '-at_install')
class TestAccountAsset(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super(TestAccountAsset, cls).setUpClass()
        today = fields.Date.today()
        cls.truck = cls.env['account.asset'].create({
            'account_asset_id': cls.company_data['default_account_assets'].id,
            'account_depreciation_id': cls.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': cls.company_data['default_account_expense'].id,
            'journal_id': cls.company_data['default_journal_misc'].id,
            'name': 'truck',
            'acquisition_date': today + relativedelta(years=-6, months=-6),
            'original_value': 10000,
            'salvage_value': 2500,
            'method_number': 10,
            'method_period': '12',
            'method': 'linear',
        })
        cls.truck.validate()
        cls.env['account.move']._autopost_draft_entries()

        cls.account_asset_model_fixedassets = cls.env['account.asset'].create({
            'account_depreciation_id': cls.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': cls.company_data['default_account_expense'].id,
            'account_asset_id': cls.company_data['default_account_assets'].id,
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'name': 'Hardware - 3 Years',
            'method_number': 3,
            'method_period': '12',
            'state': 'model',
        })


        cls.closing_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {'price_unit': 100})]
        })

        cls.env.company.loss_account_id = cls.company_data['default_account_expense'].copy()
        cls.env.company.gain_account_id = cls.company_data['default_account_revenue'].copy()
        cls.assert_counterpart_account_id = cls.company_data['default_account_expense'].copy().id

        cls.env.user.groups_id += cls.env.ref('analytic.group_analytic_accounting')
        analytic_plan = cls.env['account.analytic.plan'].create({
            'name': "Default Plan",
        })
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': "Test Account",
            'plan_id': analytic_plan.id,
        })

    def update_form_values(self, asset_form):
        for i in range(len(asset_form.depreciation_move_ids)):
            with asset_form.depreciation_move_ids.edit(i) as line_edit:
                line_edit.asset_remaining_value

    def test_account_asset_no_tax(self):
        self.account_asset_model_fixedassets.account_depreciation_expense_id.tax_ids = self.tax_purchase_a
        CEO_car = self.env['account.asset'].create({
            'salvage_value': 2000.0,
            'state': 'open',
            'method_period': '12',
            'method_number': 5,
            'name': "CEO's Car",
            'original_value': 12000.0,
            'model_id': self.account_asset_model_fixedassets.id,
        })
        CEO_car._onchange_model_id()
        CEO_car.prorata_computation_type = 'constant_periods'
        CEO_car.method_number = 5

        # In order to test the process of Account Asset, I perform a action to confirm Account Asset.
        CEO_car.validate()

        self.assertFalse(any(CEO_car.depreciation_move_ids.line_ids.mapped('tax_line_id')))

    def test_00_account_asset(self):
        """Test the lifecycle of an asset"""
        CEO_car = self.env['account.asset'].create({
            'salvage_value': 2000.0,
            'state': 'open',
            'method_period': '12',
            'method_number': 5,
            'name': "CEO's Car",
            'original_value': 12000.0,
            'model_id': self.account_asset_model_fixedassets.id,
        })
        CEO_car._onchange_model_id()
        CEO_car.prorata_computation_type = 'constant_periods'
        CEO_car.method_number = 5

        # In order to test the process of Account Asset, I perform a action to confirm Account Asset.
        CEO_car.validate()

        # TOFIX: the method validate() makes the field account.asset.asset_type
        # dirty, but this field has to be flushed in CEO_car's environment.
        # This is because the field 'asset_type' is stored, computed and
        # context-dependent, which explains why its value must be retrieved
        # from the right environment.
        CEO_car.flush_recordset()

        # I check Asset is now in Open state.
        self.assertEqual(CEO_car.state, 'open',
                         'Asset should be in Open state')

        # I compute depreciation lines for asset of CEOs Car.
        self.assertEqual(CEO_car.method_number + 1, len(CEO_car.depreciation_move_ids),
                         'Depreciation lines not created correctly')

        # Check that auto_post is set on the entries, in the future, and we cannot post them.
        self.assertTrue(all(CEO_car.depreciation_move_ids.mapped(lambda m: m.auto_post != 'no')))
        with self.assertRaises(UserError):
            CEO_car.depreciation_move_ids.action_post()

        # I Check that After creating all the moves of depreciation lines the state "Running".
        CEO_car.depreciation_move_ids.write({'auto_post': 'no'})
        CEO_car.depreciation_move_ids.action_post()
        self.assertEqual(CEO_car.state, 'open',
                         'State of asset should be runing')
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 2000,
            'value_residual': 0,
            'salvage_value': 2000,
        }])

        self.assertRecordValues(CEO_car.depreciation_move_ids.sorted(lambda l: l.date), [{
            'amount_total': 1000,
            'asset_remaining_value': 9000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 7000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 5000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 3000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 1000,
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 0,
        }])

        # Revert posted entries in order to be able to close
        CEO_car.depreciation_move_ids._reverse_moves(cancel=True)
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 12000,
            'value_residual': 10000,
            'salvage_value': 2000,
        }])
        reversed_moves_values = [{
            'amount_total': 1000,
            'asset_remaining_value': 11000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 13000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 15000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 17000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 19000,
            'state': 'posted',
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 20000,
            'state': 'posted',
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 19000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 17000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 15000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 13000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 11000,
            'state': 'posted',
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 10000,
            'state': 'posted',
        }, {
            'amount_total': 10000,
            'asset_remaining_value': 0,
            'state': 'draft',
        }]

        self.assertRecordValues(CEO_car.depreciation_move_ids.sorted(lambda l: l.date), reversed_moves_values)
        self.assertRecordValues(CEO_car.depreciation_move_ids.filtered(lambda l: l.state == 'draft').line_ids, [{
            'debit': 0,
            'credit': 10000,
            'account_id': CEO_car.account_depreciation_id.id,
        }, {
            'debit': 10000,
            'credit': 0,
            'account_id': CEO_car.account_depreciation_expense_id.id,
        }])

        # Close
        CEO_car.set_to_close(self.closing_invoice.invoice_line_ids, date=fields.Date.today() + relativedelta(days=-1))
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 12000,
            'value_residual': 10000,
            'salvage_value': 2000,
        }])
        self.assertRecordValues(CEO_car.depreciation_move_ids.sorted(lambda l: (l.date, l.id)), [{
            'amount_total': 12000,
            'asset_remaining_value': 0,
            'state': 'draft',
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 1000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 3000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 5000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 7000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 9000,
            'state': 'posted',
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 10000,
            'state': 'posted',
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 9000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 7000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 5000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 3000,
            'state': 'posted',
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 1000,
            'state': 'posted',
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 0,
            'state': 'posted',
        }])
        closing_move = CEO_car.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 12000,
            'account_id': CEO_car.account_asset_id.id,
        }, {
            'debit': 0,
            'credit': 0,
            'account_id': CEO_car.account_depreciation_id.id,
        }, {
            'debit': 100,
            'credit': 0,
            'account_id': self.closing_invoice.invoice_line_ids.account_id.id,
        }, {
            'debit': 11900,
            'credit': 0,
            'account_id': self.env.company.loss_account_id.id,
        }])
        closing_move.action_post()
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 0,
            'value_residual': 0,
            'salvage_value': 2000,
        }])

    def test_00_account_asset_new(self):
        """Test the lifecycle of an asset"""
        CEO_car = self.env['account.asset'].create({
            'salvage_value': 2000.0,
            'state': 'open',
            'method_period': '12',
            'method_number': 5,
            'name': "CEO's Car",
            'original_value': 12000.0,
            'model_id': self.account_asset_model_fixedassets.id,
        })
        CEO_car._onchange_model_id()
        CEO_car.prorata_computation_type = 'constant_periods'
        CEO_car.method_number = 5

        # In order to test the process of Account Asset, I perform a action to confirm Account Asset.
        CEO_car.validate()

        # I Check that After creating all the moves of depreciation lines the state of the asset is "Running".
        CEO_car.depreciation_move_ids.write({'auto_post': 'no'})
        CEO_car.depreciation_move_ids.action_post()
        self.assertEqual(CEO_car.state, 'open',
                         'State of the asset should be running')
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 2000,
            'value_residual': 0,
            'salvage_value': 2000,
        }])
        self.assertRecordValues(CEO_car.depreciation_move_ids.sorted(lambda l: l.date), [{
            'amount_total': 1000,
            'asset_remaining_value': 9000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 7000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 5000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 3000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': 1000,
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 0,
        }])

        # Close
        CEO_car.set_to_close(self.closing_invoice.invoice_line_ids, date=fields.Date.today() + relativedelta(days=30))
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 12000,
            'value_residual': 10000,
            'salvage_value': 2000,
        }])
        self.assertRecordValues(CEO_car.depreciation_move_ids.sorted(lambda l: (l.date, l.id)), [{
            'amount_total': 166.67,
            'asset_remaining_value': 9833.33,
            'state': 'draft',
        }, {
            'amount_total': 12000,
            'asset_remaining_value': 0,
            'state': 'draft',
        }])
        closing_move = max(CEO_car.depreciation_move_ids, key=lambda m: (m.date, m.id))
        self.assertRecordValues(closing_move, [{
            'date': fields.Date.today() + relativedelta(days=30),
        }])
        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 12000,
            'account_id': CEO_car.account_asset_id.id,
        }, {
            'debit': 166.67,
            'credit': 0,
            'account_id': CEO_car.account_depreciation_id.id,
        }, {
            'debit': 100,
            'credit': 0,
            'account_id': self.closing_invoice.invoice_line_ids.account_id.id,
        }, {
            'debit': 11733.33,
            'credit': 0,
            'account_id': self.env.company.loss_account_id.id,
        }])
        CEO_car.depreciation_move_ids.auto_post = 'no'
        CEO_car.depreciation_move_ids.action_post()
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 0,
            'value_residual': 0,
            'salvage_value': 2000,
            'state': 'close',
        }])

    def test_01_account_asset(self):
        """ Test if an an asset is created when an invoice is validated with an
        item on an account for generating entries.
        """
        account_asset_model = self.env['account.asset'].create({
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'name': 'Typical car - 3 Years',
            'method_number': 3,
            'method_period': '12',
            'prorata_computation_type': 'daily_computation',
            'state': 'model',
        })

        # The account needs a default model for the invoice to validate the revenue
        self.company_data['default_account_assets'].create_asset = 'validate'
        self.company_data['default_account_assets'].asset_model = account_asset_model

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': '2020-12-31',
            'invoice_line_ids': [(0, 0, {
                'name': 'Very little red car',
                'account_id': self.company_data['default_account_assets'].id,
                'price_unit': 450,
                'quantity': 1,
            })],
        })
        invoice.action_post()

        asset = invoice.asset_ids
        self.assertEqual(len(asset), 1, 'One and only one asset should have been created from invoice.')

        self.assertTrue(asset.state == 'open',
                        'Asset should be in Open state')
        first_invoice_line = invoice.invoice_line_ids[0]
        self.assertEqual(asset.original_value, first_invoice_line.price_subtotal,
                         'Asset value is not same as invoice line.')

        # I check data in move line and depreciation line.
        first_depreciation_line = asset.depreciation_move_ids.sorted(lambda r: r.id)[0]
        self.assertAlmostEqual(first_depreciation_line.asset_remaining_value, asset.original_value - first_depreciation_line.amount_total,
                               msg='Remaining value is incorrect.')
        self.assertAlmostEqual(first_depreciation_line.asset_depreciated_value, first_depreciation_line.amount_total,
                               msg='Depreciated value is incorrect.')

        # I check next installment date.
        last_depreciation_date = first_depreciation_line.date
        installment_date = last_depreciation_date + relativedelta(months=+int(asset.method_period))
        self.assertEqual(asset.depreciation_move_ids.sorted(lambda r: r.id)[1].date, installment_date,
                         'Installment date is incorrect.')

    def test_02_account_asset(self):
        """Test the lifecycle of an asset"""
        CEO_car = self.env['account.asset'].create({
            'salvage_value': 2000.0,
            'state': 'open',
            'method_period': '12',
            'method_number': 5,
            'name': "CEO's Car",
            'original_value': 12000.0,
            'model_id': self.account_asset_model_fixedassets.id,
            'acquisition_date': '2010-01-31',
            'already_depreciated_amount_import': 10000.0,
        })
        CEO_car._onchange_model_id()

        CEO_car.validate()
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 2000,
            'value_residual': 0,
            'salvage_value': 2000,
        }])
        self.assertFalse(CEO_car.depreciation_move_ids)
        CEO_car.set_to_close(self.closing_invoice.invoice_line_ids)
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 2000,
            'value_residual': 0,
            'salvage_value': 2000,
        }])
        closing_move = CEO_car.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 12000,
            'account_id': CEO_car.account_asset_id.id,
        }, {
            'debit': 10000,
            'credit': 0,
            'account_id': CEO_car.account_depreciation_id.id,
        }, {
            'debit': 100,
            'credit': 0,
            'account_id': self.closing_invoice.invoice_line_ids.account_id.id,
        }, {
            'debit': 1900,
            'credit': 0,
            'account_id': CEO_car.company_id.loss_account_id.id,
        }])
        closing_move.action_post()
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 0,
            'value_residual': 0,
            'salvage_value': 2000,
        }])

    def test_03_account_asset(self):
        """Test the salvage of an asset with gain"""
        CEO_car = self.env['account.asset'].create({
            'salvage_value': 0,
            'state': 'open',
            'method_period': '12',
            'method_number': 5,
            'name': "CEO's Car",
            'original_value': 12000.0,
            'model_id': self.account_asset_model_fixedassets.id,
            'acquisition_date': '2010-01-31',
            'already_depreciated_amount_import': 12000.0,
        })
        CEO_car._onchange_model_id()

        CEO_car.validate()
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 0,
            'value_residual': 0,
            'salvage_value': 0,
        }])
        self.assertFalse(CEO_car.depreciation_move_ids)
        CEO_car.set_to_close(self.closing_invoice.invoice_line_ids)
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 0,
            'value_residual': 0,
            'salvage_value': 0,
        }])
        closing_move = CEO_car.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 12000,
            'account_id': CEO_car.account_asset_id.id,
        }, {
            'debit': 12000,
            'credit': 0,
            'account_id': CEO_car.account_depreciation_id.id,
        }, {
            'debit': 100,
            'credit': 0,
            'account_id': self.closing_invoice.invoice_line_ids.account_id.id,
        }, {
            'debit': 0,
            'credit': 100,
            'account_id': CEO_car.company_id.gain_account_id.id,
        }])
        closing_move.action_post()
        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 0,
            'value_residual': 0,
            'salvage_value': 0,
        }])

    def test_04_account_asset(self):
        """Test the salvage of an asset with gain"""
        CEO_car = self.env['account.asset'].create({
            'salvage_value': 0,
            'state': 'open',
            'method_period': '12',
            'method_number': 5,
            'name': "CEO's Car",
            'original_value': 800.0,
            'model_id': self.account_asset_model_fixedassets.id,
            'acquisition_date': '2021-01-01',
            'already_depreciated_amount_import': 300.0,
        })
        CEO_car._onchange_model_id()
        CEO_car.method_number = 5

        CEO_car.validate()
        self.assertRecordValues(CEO_car, [{
            'original_value': 800,
            'book_value': 500,
            'value_residual': 500,
            'salvage_value': 0,
        }])
        self.assertEqual(len(CEO_car.depreciation_move_ids), 4)
        CEO_car.set_to_close(self.closing_invoice.invoice_line_ids, date=fields.Date.today() + relativedelta(months=-6, days=-1))
        self.assertRecordValues(CEO_car, [{
            'original_value': 800,
            'book_value': 500,
            'value_residual': 500,
            'salvage_value': 0,
        }])
        closing_move = CEO_car.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 800,
            'account_id': CEO_car.account_asset_id.id,
        }, {
            'debit': 300,
            'credit': 0,
            'account_id': CEO_car.account_depreciation_id.id,
        }, {
            'debit': 100,
            'credit': 0,
            'account_id': self.closing_invoice.invoice_line_ids.account_id.id,
        }, {
            'debit': 400,
            'credit': 0,
            'account_id': CEO_car.company_id.loss_account_id.id,
        }])
        closing_move.action_post()
        self.assertRecordValues(CEO_car, [{
            'original_value': 800,
            'book_value': 0,
            'value_residual': 0,
            'salvage_value': 0,
        }])

    def test_05_account_asset(self):
        """Test the salvage of an asset with gain"""
        CEO_car = self.env['account.asset'].create({
            'salvage_value': 0,
            'state': 'open',
            'method_period': '12',
            'method_number': 5,
            'name': "CEO's Car",
            'original_value': 1000.0,
            'model_id': self.account_asset_model_fixedassets.id,
            'acquisition_date': '2020-01-01',
        })
        CEO_car._onchange_model_id()
        CEO_car.method_number = 5
        CEO_car.account_depreciation_id = CEO_car.account_asset_id

        CEO_car.validate()
        self.assertRecordValues(CEO_car, [{
            'original_value': 1000,
            'book_value': 800,
            'value_residual': 800,
            'salvage_value': 0,
        }])
        self.assertEqual(len(CEO_car.depreciation_move_ids), 5)
        CEO_car.set_to_close(self.env['account.move.line'], date=fields.Date.today() + relativedelta(days=-1))
        self.assertRecordValues(CEO_car, [{
            'original_value': 1000,
            'book_value': 700,
            'value_residual': 700,
            'salvage_value': 0,
        }])
        closing_move = CEO_car.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 1000,
            'account_id': CEO_car.account_asset_id.id,
        }, {
            'debit': 300,
            'credit': 0,
            'account_id': CEO_car.account_depreciation_id.id,
        }, {
            'debit': 700,
            'credit': 0,
            'account_id': CEO_car.company_id.loss_account_id.id,
        }])
        closing_move.action_post()
        self.assertRecordValues(CEO_car, [{
            'original_value': 1000,
            'book_value': 0,
            'value_residual': 0,
            'salvage_value': 0,
        }])

    def test_06_account_asset(self):
        """Test the correct computation of asset amounts"""
        asset_account = self.env['account.account'].create({
            "name": "test_06_account_asset",
            "code": "test.06.account.asset",
            "account_type": 'asset_non_current',
            "create_asset": "no",
            "multiple_assets_per_line": True,
        })

        CEO_car = self.env['account.asset'].create({
            'salvage_value': 0,
            'state': 'draft',
            'method_period': '12',
            'method_number': 4,
            'name': "CEO's Car",
            'original_value': 1000.0,
            'acquisition_date': fields.Date.today() - relativedelta(years=3),
            'account_asset_id': asset_account.id,
            'account_depreciation_id': self.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': asset_account.id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'prorata_computation_type': 'none',
        })

        CEO_car.validate()
        posted_entries = len(CEO_car.depreciation_move_ids.filtered(lambda x: x.state == 'posted'))
        self.assertEqual(posted_entries, 3)

        self.assertRecordValues(CEO_car, [{
            'original_value': 1000,
            'book_value': 250,
            'value_residual': 250,
            'salvage_value': 0,
        }])

    def test_account_asset_cancel(self):
        """Test the cancellation of an asset"""
        today = fields.Date.today()
        CEO_car = self.env['account.asset'].create({
            'salvage_value': 2000.0,
            'state': 'open',
            'method_period': '12',
            'method_number': 5,
            'name': "CEO's Car",
            'original_value': 12000.0,
            'model_id': self.account_asset_model_fixedassets.id,
            'acquisition_date': today + relativedelta(years=-3, month=1, day=1),
        })
        CEO_car._onchange_model_id()
        CEO_car.method_number = 5
        CEO_car.validate()

        self.assertRecordValues(CEO_car, [{
            'original_value': 12000,
            'book_value': 6000,
            'value_residual': 4000,
            'salvage_value': 2000,
        }])
        CEO_car.set_to_cancelled()

        self.assertEqual(CEO_car.state, 'cancelled')
        self.assertFalse(CEO_car.depreciation_move_ids)

        # Hashed journals should reverse entries instead of deleting
        Hashed_car = CEO_car.copy()
        Hashed_car.write({
            'original_value': 12000.0,
            'method_number': 5,
            'name': "Hashed Car",
            'journal_id': CEO_car.journal_id.copy().id,
            'acquisition_date': today + relativedelta(years=-3, month=1, day=1),
        })
        Hashed_car.journal_id.restrict_mode_hash_table = True
        Hashed_car.validate()

        for i in range(0, 4):
            self.assertFalse(Hashed_car.depreciation_move_ids[i].reversal_move_id)

        Hashed_car.set_to_cancelled()

        self.assertEqual(Hashed_car.state, 'cancelled')
        for i in range(0, 2):
            self.assertTrue(Hashed_car.depreciation_move_ids[i].reversal_move_id.id > 0 or Hashed_car.depreciation_move_ids[i].reversed_entry_id.id > 0)

        # The depreciation schedule report should not contain cancelled assets
        report = self.env.ref('account_asset.assets_report')
        options = self._generate_options(report, today + relativedelta(years=-6, month=1, day=1), today + relativedelta(years=+4, month=12, day=31))
        lines = report._get_lines({**options, **{'unfold_all': False, 'all_entries': True}})
        assets_in_report = [x['name'] for x in lines[:-1]]

        self.assertNotIn(CEO_car.name, assets_in_report)
        self.assertNotIn(Hashed_car.name, assets_in_report)

        # When a lock date is applied, only the moves before the date are reversed, others are deleted
        Locked_car = CEO_car.copy()
        Locked_car.write({
            'original_value': 12000.0,
            'method_number': 10,
            'name': "Locked Car",
            'acquisition_date': today + relativedelta(years=-3, month=1, day=1),
        })
        Locked_car.validate()
        Locked_car.company_id.fiscalyear_lock_date = today + relativedelta(years=-1)

        self.assertEqual(len(Locked_car.depreciation_move_ids), 10)
        Locked_car.set_to_cancelled()
        self.assertRecordValues(Locked_car, [{
            'state': 'cancelled',
            'book_value': 12000.0,
            'value_residual': 10000,
            'salvage_value': 2000,
        }])
        self.assertEqual(len(Locked_car.depreciation_move_ids), 4)
        for depreciation in Locked_car.depreciation_move_ids:
            self.assertTrue(depreciation.reversal_move_id or depreciation.reversed_entry_id)


    def test_asset_form(self):
        """Test the form view of assets"""
        asset_form = Form(self.env['account.asset'])
        asset_form.name = "Test Asset"
        asset_form.original_value = 10000
        asset_form.account_depreciation_id = self.company_data['default_account_assets']
        asset_form.account_depreciation_expense_id = self.company_data['default_account_expense']
        asset_form.journal_id = self.company_data['default_journal_misc']
        asset_form.prorata_computation_type = 'none'
        asset = asset_form.save()
        asset.validate()

        # Test that the depreciations are created upon validation of the asset according to the default values
        self.assertEqual(len(asset.depreciation_move_ids), 5)
        for move in asset.depreciation_move_ids:
            self.assertEqual(move.amount_total, 2000)

        # Test that we cannot validate an asset with non zero remaining value of the last depreciation line
        asset_form = Form(asset)
        with self.assertRaises(UserError):
            with self.cr.savepoint():
                with asset_form.depreciation_move_ids.edit(4) as line_edit:
                    line_edit.depreciation_value = 1000.0
                asset_form.save()

        # ... but we can with a zero remaining value on the last line.
        asset_form = Form(asset)
        with asset_form.depreciation_move_ids.edit(4) as line_edit:
            line_edit.depreciation_value = 1000.0
        with asset_form.depreciation_move_ids.edit(3) as line_edit:
            line_edit.depreciation_value = 3000.0
        self.update_form_values(asset_form)
        asset_form.save()

    def test_asset_from_move_line_form(self):
        """Test that the asset is correcly created from a move line"""

        move_ids = self.env['account.move'].create([{
            'ref': 'line1',
            'line_ids': [
                (0, 0, {
                    'account_id': self.company_data['default_account_expense'].id,
                    'debit': 300,
                    'name': 'Furniture',
                }),
                (0, 0, {
                    'account_id': self.company_data['default_account_assets'].id,
                    'credit': 300,
                }),
            ]
        }, {
            'ref': 'line2',
            'line_ids': [
                (0, 0, {
                    'account_id': self.company_data['default_account_expense'].id,
                    'debit': 600,
                    'name': 'Furniture too',
                }),
                (0, 0, {
                    'account_id': self.company_data['default_account_assets'].id,
                    'credit': 600,
                }),
            ]
        },
        ])
        move_ids.action_post()
        move_line_ids = move_ids.mapped('line_ids').filtered(lambda x: x.debit)

        asset_form = Form(self.env['account.asset'].with_context(default_original_move_line_ids=move_line_ids.ids))
        asset_form.original_move_line_ids = move_line_ids
        asset_form.account_depreciation_expense_id = self.company_data['default_account_expense']

        asset = asset_form.save()
        self.assertEqual(asset.value_residual, 900.0)
        self.assertIn(asset.name, ['Furniture', 'Furniture too'])
        self.assertEqual(asset.journal_id.type, 'general')
        self.assertEqual(asset.account_asset_id, self.company_data['default_account_expense'])
        self.assertEqual(asset.account_depreciation_id, self.company_data['default_account_expense'])
        self.assertEqual(asset.account_depreciation_expense_id, self.company_data['default_account_expense'])

    def test_asset_modify_value_00(self):
        """Test the values of the asset and value increase 'assets' after a
        modification of residual and/or salvage values.
        Increase the residual value, increase the salvage value"""
        self.assertEqual(self.truck.value_residual, 3000)
        self.assertEqual(self.truck.salvage_value, 2500)

        self.env['asset.modify'].create({
            'name': 'New beautiful sticker :D',
            'asset_id': self.truck.id,
            'value_residual': 4000,
            'salvage_value': 3000,
            'date':  fields.Date.today() + relativedelta(months=-6, days=-1),
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()
        self.assertEqual(self.truck.value_residual, 3000)
        self.assertEqual(self.truck.salvage_value, 2500)
        self.assertEqual(self.truck.children_ids.value_residual, 1000)
        self.assertEqual(self.truck.children_ids.salvage_value, 500)

    def test_asset_modify_value_01(self):
        "Decrease the residual value, decrease the salvage value"
        self.env['asset.modify'].create({
            'name': "Accident :'(",
            'date':  fields.Date.today() + relativedelta(months=-6, days=-1),
            'asset_id': self.truck.id,
            'value_residual': 1000,
            'salvage_value': 2000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()
        self.assertEqual(self.truck.value_residual, 1000)
        self.assertEqual(self.truck.salvage_value, 2000)
        self.assertEqual(self.truck.children_ids.value_residual, 0)
        self.assertEqual(self.truck.children_ids.salvage_value, 0)
        self.assertEqual(max(self.truck.depreciation_move_ids.filtered(lambda m: m.state == 'posted'), key=lambda m: (m.date, m.id)).amount_total, 2500)

    def test_asset_modify_value_02(self):
        "Decrease the residual value, increase the salvage value; same book value"
        self.env['asset.modify'].create({
            'name': "Don't wanna depreciate all of it",
            'asset_id': self.truck.id,
            'date':  fields.Date.today() + relativedelta(months=-6, days=-1),
            'value_residual': 1000,
            'salvage_value': 4500,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()
        self.assertEqual(self.truck.value_residual, 1000)
        self.assertEqual(self.truck.salvage_value, 4500)
        self.assertEqual(self.truck.children_ids.value_residual, 0)
        self.assertEqual(self.truck.children_ids.salvage_value, 0)

    def test_asset_modify_value_03(self):
        "Decrease the residual value, increase the salvage value; increase of book value"
        self.env['asset.modify'].create({
            'name': "Some aliens did something to my truck",
            'asset_id': self.truck.id,
            'date':  fields.Date.today() + relativedelta(months=-6, days=-1),
            'value_residual': 1000,
            'salvage_value': 6000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()
        self.assertEqual(self.truck.value_residual, 1000)
        self.assertEqual(self.truck.salvage_value, 4500)
        self.assertEqual(self.truck.children_ids.value_residual, 0)
        self.assertEqual(self.truck.children_ids.salvage_value, 1500)

    def test_asset_modify_value_04(self):
        "Increase the residual value, decrease the salvage value; increase of book value"
        self.env['asset.modify'].create({
            'name': 'GODZILA IS REAL!',
            'asset_id': self.truck.id,
            'date':  fields.Date.today() + relativedelta(months=-6, days=-1),
            'value_residual': 4000,
            'salvage_value': 2000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()
        self.assertEqual(self.truck.value_residual, 3500)
        self.assertEqual(self.truck.salvage_value, 2000)
        self.assertEqual(self.truck.children_ids.value_residual, 500)
        self.assertEqual(self.truck.children_ids.salvage_value, 0)

    def test_asset_modify_report(self):
        """Test the asset value modification flows"""
        #           PY      +   -  Final    PY     +    - Final Bookvalue
        #   -6       0  10000   0  10000     0   750    0   750      9250
        #   -5   10000      0   0  10000   750   750    0  1500      8500
        #   -4   10000      0   0  10000  1500   750    0  2250      7750
        #   -3   10000      0   0  10000  2250   750    0  3000      7000
        #   -2   10000      0   0  10000  3000   750    0  3750      6250
        #   -1   10000      0   0  10000  3750   750    0  4500      5500
        #    0   10000      0   0  10000  4500   750    0  5250      4750  <-- today
        #    1   10000      0   0  10000  5250   750    0  6000      4000
        #    2   10000      0   0  10000  6000   750    0  6750      3250
        #    3   10000      0   0  10000  6750   750    0  7500      2500

        today = fields.Date.today()

        report = self.env.ref('account_asset.assets_report')
        # TEST REPORT
        # look at all period, with unposted entries
        options = self._generate_options(report, today + relativedelta(years=-6, month=1, day=1), today + relativedelta(years=+4, month=12, day=31))
        lines = report._get_lines({**options, **{'unfold_all': False, 'all_entries': True}})
        self.assertListEqual([    0.0, 10000.0,     0.0, 10000.0,     0.0,  7500.0,     0.0,  7500.0,  2500.0],
                             [x['no_format'] for x in lines[0]['columns'][4:]])

        # look at all period, without unposted entries
        options = self._generate_options(report, today + relativedelta(years=-6, month=1, day=1), today + relativedelta(years=+4, month=12, day=31))
        lines = report._get_lines({**options, **{'unfold_all': False, 'all_entries': False}})
        self.assertListEqual([    0.0, 10000.0,     0.0, 10000.0,     0.0,  4500.0,     0.0,  4500.0,  5500.0],
                             [x['no_format'] for x in lines[0]['columns'][4:]])

        # look only at this period
        options = self._generate_options(report, today + relativedelta(years=0, month=1, day=1), today + relativedelta(years=0, month=12, day=31))
        lines = report._get_lines({**options, **{'unfold_all': False, 'all_entries': True}})
        self.assertListEqual([10000.0,     0.0,     0.0, 10000.0,  4500.0,   750.0,     0.0,  5250.0,  4750.0],
                             [x['no_format'] for x in lines[0]['columns'][4:]])

        # test value increase
        #           PY     +   -  Final    PY     +    - Final Bookvalue
        #   -6       0 10000   0  10000         750    0   750      9250
        #   -5   10000     0   0  10000   750   750    0  1500      8500
        #   -4   10000     0   0  10000  1500   750    0  2250      7750
        #   -3   10000     0   0  10000  2250   750    0  3000      7000
        #   -2   10000     0   0  10000  3000   750    0  3750      6250
        #   -1   10000  1500   0  10000  3750   950    0  4700      6800
        #    0   10000     0   0  11500  4700   950    0  5650      5850  <--  today
        #    1   11500     0   0  11500  5650   950    0  6600      4900
        #    2   11500     0   0  11500  6600   950    0  7550      3950
        #    3   11500     0   0  11500  7550   950    0  8500      3000
        self.assertEqual(self.truck.value_residual, 3000)
        self.assertEqual(self.truck.salvage_value, 2500)
        self.env['asset.modify'].create({
            'name': 'New beautiful sticker :D',
            'asset_id': self.truck.id,
            'date': fields.Date.today() + relativedelta(years=-1, months=-6, days=-1),
            'value_residual': 4000,
            'salvage_value': 3000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        self.assertEqual(self.truck.value_residual + sum(self.truck.children_ids.mapped('value_residual')), 3800)
        self.assertEqual(self.truck.salvage_value + sum(self.truck.children_ids.mapped('salvage_value')), 3000)

        # look at all period, with unposted entries
        options = self._generate_options(report, today + relativedelta(years=-6, months=-6), today + relativedelta(years=+4, month=12, day=31))
        lines = report._get_lines({**options, **{'unfold_all': False, 'all_entries': True}})
        self.assertListEqual([0.0, 11500.0, 0.0, 11500.0, 0.0, 8500.0, 0.0, 8500.0, 3000.0],
                             [x['no_format'] for x in lines[0]['columns'][4:]])
        self.assertEqual('10 y', lines[1]['columns'][3]['name'], 'Depreciation Rate = 10%')

        # look only at this period
        options = self._generate_options(report, today + relativedelta(years=0, month=1, day=1), today + relativedelta(years=0, month=12, day=31))
        lines = report._get_lines({**options, **{'unfold_all': False, 'all_entries': True}})
        self.assertListEqual([11500.0, 0.0, 0.0, 11500.0, 4700.0, 950.0, 0.0, 5650.0, 5850.0],
                             [x['no_format'] for x in lines[0]['columns'][4:]])

        # test value decrease
        self.env['asset.modify'].create({
            'name': "Huge scratch on beautiful sticker :'( It is ruined",
            'date': fields.Date.today() + relativedelta(months=-6, days=-1),
            'asset_id': self.truck.children_ids.id,
            'value_residual': 0,
            'salvage_value': 500,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()
        self.env['asset.modify'].create({
            'name': "Huge scratch on beautiful sticker :'( It went through...",
            'date': fields.Date.today() + relativedelta(months=-6, days=-1),
            'asset_id': self.truck.id,
            'value_residual': 1000,
            'salvage_value': 2500,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()
        self.assertEqual(self.truck.value_residual + sum(self.truck.children_ids.mapped('value_residual')), 1000)
        self.assertEqual(self.truck.salvage_value + sum(self.truck.children_ids.mapped('salvage_value')), 3000)

        # look at all period, with unposted entries
        options = self._generate_options(report, today + relativedelta(years=-6, month=1, day=1), today + relativedelta(years=+4, month=12, day=31))
        lines = report._get_lines({**options, **{'unfold_all': False, 'all_entries': True}})
        self.assertListEqual([0.0, 11500.0, 0.0, 11500.0, 0.0, 8500.0, 0.0, 8500.0, 3000.0],
                             [x['no_format'] for x in lines[0]['columns'][4:]])

        # look only at previous period
        options = self._generate_options(report, today + relativedelta(years=-1, month=1, day=1), today + relativedelta(years=-1, month=12, day=31))
        lines = report._get_lines({**options, **{'unfold_all': False, 'all_entries': True}})
        self.assertListEqual([10000.0, 1500.0, 0.0, 11500.0, 3750.0, 3750.0, 0.0, 7500.0, 4000.0],
                             [x['no_format'] for x in lines[0]['columns'][4:]])

    def test_asset_pause_resume(self):
        """Test that depreciation remains the same after a pause and resume at a later date"""
        today = fields.Date.today()
        self.assertEqual(len(self.truck.depreciation_move_ids.filtered(lambda e: e.state == 'draft')), 4)
        self.env['asset.modify'].create({
            'date': fields.Date.today() + relativedelta(days=-1),
            'asset_id': self.truck.id,
        }).pause()
        self.assertEqual(len(self.truck.depreciation_move_ids.filtered(lambda e: e.state == 'draft')), 0)
        with freeze_time(today) as frozen_time:
            frozen_time.move_to(today + relativedelta(years=1))
            self.env['asset.modify'].with_context(resume_after_pause=True).create({
                'asset_id': self.truck.id,
            }).modify()
            self.assertEqual(len(self.truck.depreciation_move_ids.filtered(lambda e: e.state == 'posted')), 7)
            self.assertEqual(
                self.truck.depreciation_move_ids.filtered(lambda e: e.state == 'draft').mapped('amount_total'),
                [375.0, 750.0, 750.0, 750.0])

    def test_asset_modify_sell_profit(self):
        """Test that a credit is realised in the gain account when selling an asset for a sum greater than book value"""
        closing_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {'price_unit': self.truck.book_value + 100})]
        })
        self.env['asset.modify'].create({
            'asset_id': self.truck.id,
            'invoice_line_ids': closing_invoice.invoice_line_ids,
            'date': fields.Date.today() + relativedelta(months=-6, days=-1),
            'modify_action': 'sell',
        }).sell_dispose()

        closing_move = self.truck.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 10000,
            'account_id': self.truck.account_asset_id.id,
        }, {
            'debit': 4500,
            'credit': 0,
            'account_id': self.truck.account_depreciation_id.id,
        }, {
            'debit': 5600,
            'credit': 0,
            'account_id': closing_invoice.invoice_line_ids.account_id.id,
        }, {
            'debit': 0,
            'credit': 100,
            'account_id': self.env.company.gain_account_id.id,
        }])

    def test_asset_modify_sell_loss(self):
        """Test that a debit is realised in the loss account when selling an asset for a sum less than book value"""
        closing_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {'price_unit': self.truck.book_value - 100})]
        })
        self.env['asset.modify'].create({
            'asset_id': self.truck.id,
            'invoice_line_ids': closing_invoice.invoice_line_ids,
            'date': fields.Date.today() + relativedelta(months=-6, days=-1),
            'modify_action': 'sell',
        }).sell_dispose()
        closing_move = self.truck.depreciation_move_ids.filtered(lambda l: l.state == 'draft')

        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 10000,
            'account_id': self.truck.account_asset_id.id,
        }, {
            'debit': 4500,
            'credit': 0,
            'account_id': self.truck.account_depreciation_id.id,
        }, {
            'debit': 5400,
            'credit': 0,
            'account_id': closing_invoice.invoice_line_ids.account_id.id,
        }, {
            'debit': 100,
            'credit': 0,
            'account_id': self.env.company.loss_account_id.id,
        }])

    def test_asset_sale_same_account_as_invoice(self):
        """Test the sale of an asset with an invoice that has the same account as the Depreciation Account"""
        closing_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'account_id': self.truck.account_depreciation_id.id,
                    'price_unit': self.truck.book_value - 100
                })
            ]
        })
        self.env['asset.modify'].create({
            'asset_id': self.truck.id,
            'invoice_line_ids': closing_invoice.invoice_line_ids,
            'date': fields.Date.today() + relativedelta(months=-6, days=-1),
            'modify_action': 'sell',
        }).sell_dispose()
        closing_move = self.truck.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 10000,
            'account_id': self.truck.account_asset_id.id,
        }, {
            'debit': 4500,
            'credit': 0,
            'account_id': self.truck.account_depreciation_id.id,
        }, {
            'debit': 5400,
            'credit': 0,
            'account_id': closing_invoice.invoice_line_ids.account_id.id,
        }, {
            'debit': 100,
            'credit': 0,
            'account_id': self.env.company.loss_account_id.id,
        }])

        self.assertEqual(closing_move.depreciation_value, 3000, "Should be the remaining amount before the sale")

    def test_asset_modify_dispose(self):
        """Test the loss of the remaining book_value when an asset is disposed using the wizard"""
        self.env['asset.modify'].create({
            'asset_id': self.truck.id,
            'date': fields.Date.today() + relativedelta(months=-6, days=-1),
            'modify_action': 'dispose',
        }).sell_dispose()
        closing_move = self.truck.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 10000,
            'account_id': self.truck.account_asset_id.id,
        }, {
            'debit': 4500,
            'credit': 0,
            'account_id': self.truck.account_depreciation_id.id,
        }, {
            'debit': 5500,
            'credit': 0,
            'account_id': self.env.company.loss_account_id.id,
        }])

    def test_asset_reverse_depreciation(self):
        """Test the reversal of a depreciation move"""

        self.assertEqual(sum(self.truck.depreciation_move_ids.filtered(lambda m: m.state == 'posted').mapped('depreciation_value')), 4500)
        self.assertEqual(sum(self.truck.depreciation_move_ids.filtered(lambda m: m.state == 'draft').mapped('depreciation_value')), 3000)
        self.assertEqual(max(self.truck.depreciation_move_ids.filtered(lambda m: m.state == 'posted'), key=lambda m: m.date).asset_remaining_value, 3000)

        report = self.env.ref('account_asset.assets_report')
        today = fields.Date.today()

        move_to_reverse = self.truck.depreciation_move_ids.filtered(lambda m: m.state == 'posted').sorted(lambda m: m.date)[-1]
        reversed_move = move_to_reverse._reverse_moves()

        # Check that the depreciation has been reported on the next move
        min_date_draft = min(self.truck.depreciation_move_ids.filtered(lambda m: m.state == 'draft' and m.date > reversed_move.date), key=lambda m: m.date)
        self.assertEqual(move_to_reverse.asset_remaining_value - min_date_draft.depreciation_value - reversed_move.depreciation_value, min_date_draft.asset_remaining_value)
        self.assertEqual(move_to_reverse.asset_depreciated_value + min_date_draft.depreciation_value + reversed_move.depreciation_value, min_date_draft.asset_depreciated_value)

        # The amount is still there, it only has been reversed. But it has been added on the next draft move to complete the depreciation table
        self.assertEqual(sum(self.truck.depreciation_move_ids.filtered(lambda m: m.state == 'posted').mapped('depreciation_value')), 4500)
        self.assertEqual(sum(self.truck.depreciation_move_ids.filtered(lambda m: m.state == 'draft').mapped('depreciation_value')), 3000)

        # Check that the table shows fully depreciated at the end
        self.assertEqual(max(self.truck.depreciation_move_ids, key=lambda m: m.date).asset_remaining_value, 0)
        self.assertEqual(max(self.truck.depreciation_move_ids, key=lambda m: m.date).asset_depreciated_value, 7500)

        reversed_move.action_post()

        options = self._generate_options(report, today + relativedelta(years=0, month=7, day=1), today + relativedelta(years=0, month=7, day=31))
        lines = report._get_lines({**options, 'unfold_all': False, 'all_entries': True})
        # We take the reversal entry into account
        self.assertListEqual([10000.0,     0.0,     0.0, 10000.0,  4500.0,   -750.0,     0.0,  3750.0,  6250.0],
                             [x['no_format'] for x in lines[0]['columns'][4:]])

        options = self._generate_options(report, today + relativedelta(years=0, month=1, day=1), today + relativedelta(years=0, month=12, day=31))
        lines = report._get_lines({**options, 'unfold_all': False, 'all_entries': True})
        # With the report on the next entry, we get a normal depreciation amount for the year
        self.assertListEqual([10000.0,     0.0,     0.0, 10000.0,  4500.0,   750.0,     0.0,  5250.0,  4750.0],
                             [x['no_format'] for x in lines[0]['columns'][4:]])

    def test_credit_note_out_refund(self):
        """
        Test the behaviour of the asset creation when a credit note is created.
        The asset created from the credit note should be the same as the one created from the invoice
        with a negative value.
        """
        depreciation_account = self.company_data['default_account_assets'].copy()
        revenue_model = self.env['account.asset'].create({
            'account_depreciation_id': depreciation_account.id,
            'account_depreciation_expense_id': self.company_data['default_account_revenue'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'name': 'Hardware - 5 Years',
            'method_number': 5,
            'method_period': '12',
            'state': 'model',
        })

        depreciation_account.write({'create_asset': 'draft', 'asset_model': revenue_model.id})

        invoice = self.env['account.move'].create({
            'invoice_date': '2019-07-01',
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Hardware',
                'account_id': depreciation_account.id,
                'price_unit': 5000,
                'quantity': 1,
                'tax_ids': False,
            })],
        })

        invoice.action_post()
        self.assertTrue(invoice.asset_ids)

        credit_note = invoice._reverse_moves([{'invoice_date': fields.Date.today()}])
        credit_note.action_post()

        invoice_asset = invoice.asset_ids
        credit_note_asset = credit_note.asset_ids

        # check if invoice_asset still exists after validate the credit note
        self.assertTrue(invoice_asset)
        self.assertTrue(credit_note_asset)

        (invoice_asset + credit_note_asset).validate()

        self.assertRecordValues(credit_note_asset, [
            {
                'acquisition_date': invoice_asset.acquisition_date,
                'book_value': -invoice_asset.book_value,
                'value_residual': -invoice_asset.value_residual,
            }
        ])

        for invoice_asset_move, credit_note_asset_move in zip(invoice_asset.depreciation_move_ids.sorted('date'), credit_note_asset.depreciation_move_ids.sorted('date')):
            self.assertRecordValues(credit_note_asset_move, [
                {
                    'date': invoice_asset_move.date,
                    'state': invoice_asset_move.state,
                    'depreciation_value': -invoice_asset_move.depreciation_value,
                }
            ])

    def test_asset_multiple_assets_from_one_move_line_00(self):
        """ Test the creation of a as many assets as the value of
        the quantity property of a move line. """

        account = self.env['account.account'].create({
            "name": "test account",
            "code": "TEST",
            "account_type": 'asset_non_current',
            "create_asset": "draft",
            "multiple_assets_per_line": True,
        })
        move = self.env['account.move'].create({
            "partner_id": self.env['res.partner'].create({'name': 'Johny'}).id,
            "ref": "line1",
            "move_type": "in_invoice",
            "invoice_date": "2020-12-31",
            "invoice_line_ids": [
                (0, 0, {
                    "account_id": account.id,
                    "price_unit": 400.0,
                    "name": "stuff",
                    "quantity": 2,
                    "product_uom_id": self.env.ref('uom.product_uom_unit').id,
                    "tax_ids": [],
                }),
            ]
        })
        move.action_post()
        assets = move.asset_ids
        assets = sorted(assets, key=lambda i: i['original_value'], reverse=True)
        self.assertEqual(len(assets), 2, '3 assets should have been created')
        self.assertEqual(assets[0].original_value, 400.0)
        self.assertEqual(assets[1].original_value, 400.0)

    def test_asset_multiple_assets_from_one_move_line_01(self):
        """ Test the creation of a as many assets as the value of
        the quantity property of a move line. """

        account = self.env['account.account'].create({
            "name": "test account",
            "code": "TEST",
            "account_type": 'asset_non_current',
            "create_asset": "draft",
            "multiple_assets_per_line": True,
        })
        move = self.env['account.move'].create({
            "partner_id": self.env['res.partner'].create({'name': 'Johny'}).id,
            "ref": "line1",
            "move_type": "in_invoice",
            "invoice_date": "2020-12-31",
            "invoice_line_ids": [
                (0, 0, {
                    "account_id": account.id,
                    "name": "stuff",
                    "quantity": 3.0,
                    "price_unit": 1000.0,
                    "product_uom_id": self.env.ref('uom.product_uom_categ_unit').id,
                }),
                (0, 0, {
                    'account_id': self.company_data['default_account_assets'].id,
                    "name": "stuff",
                    'quantity': 1.0,
                    'price_unit': -500.0,
                }),
            ]
        })
        move.action_post()
        self.assertEqual(sum(asset.original_value for asset in move.asset_ids), move.line_ids[0].debit)

    def test_asset_credit_note(self):
        """Test the generated entries created from an in_refund invoice with asset"""
        asset_model = self.env['account.asset'].create({
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'account_asset_id': self.company_data['default_account_assets'].id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'name': 'Small car - 3 Years',
            'method_number': 3,
            'method_period': '12',
            'state': 'model',
        })

        self.company_data['default_account_assets'].create_asset = "validate"
        self.company_data['default_account_assets'].asset_model = asset_model

        invoice = self.env['account.move'].create({
            'move_type': 'in_refund',
            'invoice_date': '2020-01-01',
            'date': '2020-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Very little red car',
                'account_id': self.company_data['default_account_assets'].id,
                'price_unit': 450,
                'quantity': 1,
            })],
        })
        invoice.action_post()
        depreciation_lines = self.env['account.move.line'].search([
            ('account_id', '=', asset_model.account_depreciation_id.id),
            ('move_id.asset_id', '=', invoice.asset_ids.id),
            ('debit', '=', 150),
        ])
        self.assertEqual(
            len(depreciation_lines), 3,
            'Three entries with a debit of 150 must be created on the Deferred Expense Account'
        )

    def test_asset_partial_credit_note(self):
        """Test partial credit note on an in invoice that has generated draft assets.

        Test case:
        - Create in invoice with the following lines:

            Product  |  Unit Price  |  Quantity  |  Multiple assets
          ---------------------------------------------------------
           Product B |     200      |      4     |       TRUE
           Product A |     100      |      7     |       FALSE
           Product A |     100      |      5     |       TRUE
           Product A |     150      |      6     |       TRUE
           Product A |     100      |      7     |       FALSE

        - Add a credit note with the following lines:

            Product  |  Unit Price  |  Quantity
          ---------------------------------------
           Product A |     100      |      1
           Product A |     150      |      2
           Product A |     100      |      7
        """
        asset_model = self.env['account.asset'].create({
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_sale'].id,
            'name': 'Maintenance Contract - 3 Years',
            'method_number': 3,
            'method_period': '12',
            'prorata_computation_type': 'none',
            'state': 'model',
        })
        self.company_data['default_account_assets'].create_asset = 'draft'
        self.company_data['default_account_assets'].asset_model = asset_model
        account_assets_multiple = self.company_data['default_account_assets'].copy()
        account_assets_multiple.multiple_assets_per_line = True

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'default_code': 'PA',
            'lst_price': 100.0,
            'standard_price': 100.0,
        })
        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'default_code': 'PB',
            'lst_price': 200.0,
            'standard_price': 200.0,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2020-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': product_b.id,
                    'name': 'Product B',
                    'account_id': account_assets_multiple.id,
                    'price_unit': 200.0,
                    'quantity': 4,
                }),
                (0, 0, {
                    'product_id': product_a.id,
                    'name': 'Product A',
                    'account_id': self.company_data['default_account_assets'].id,
                    'price_unit': 100.0,
                    'quantity': 7,
                }),
                (0, 0, {
                    'product_id': product_a.id,
                    'name': 'Product A',
                    'account_id': account_assets_multiple.id,
                    'price_unit': 100.0,
                    'quantity': 5,
                }),
                (0, 0, {
                    'product_id': product_a.id,
                    'name': 'Product A',
                    'account_id': account_assets_multiple.id,
                    'price_unit': 150.0,
                    'quantity': 6,
                }),
                (0, 0, {
                    'product_id': product_a.id,
                    'name': 'Product A',
                    'account_id': self.company_data['default_account_assets'].id,
                    'price_unit': 100.0,
                    'quantity': 7,
                }),
            ],
        })
        invoice.action_post()
        product_a_100_lines = invoice.line_ids.filtered(lambda l: l.product_id == product_a and l.price_unit == 100.0)
        product_a_150_lines = invoice.line_ids.filtered(lambda l: l.product_id == product_a and l.price_unit == 150.0)
        product_b_lines = invoice.line_ids.filtered(lambda l: l.product_id == product_b)
        self.assertEqual(len(invoice.line_ids.mapped(lambda l: l.asset_ids)), 17)
        self.assertEqual(len(product_b_lines.asset_ids), 4)
        self.assertEqual(len(product_a_100_lines.asset_ids), 7)
        self.assertEqual(len(product_a_150_lines.asset_ids), 6)
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
        self.assertEqual(len(invoice.line_ids.mapped(lambda l: l.asset_ids)), 17)
        self.assertEqual(len(product_b_lines.asset_ids), 4)
        self.assertEqual(len(product_a_100_lines.asset_ids), 7)
        self.assertEqual(len(product_a_150_lines.asset_ids), 6)

    def test_asset_with_non_deductible_tax(self):
        """Test that the assets' original_value and non_deductible_tax_value are correctly computed
        from a move line with a non-deductible tax."""

        asset_account = self.company_data['default_account_assets']
        non_deductible_tax = self.env['account.tax'].create({
            'name': 'Non-deductible Tax',
            'amount': 21,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': True
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': False
                }),
                Command.create({
                    'factor_percent': 50,
                    'repartition_type': 'tax',
                    'use_in_tax_closing': True
                }),
            ],
        })
        asset_account.tax_ids = non_deductible_tax

        # 1. Automatic creation
        asset_account.create_asset = 'draft'
        asset_account.asset_model = self.account_asset_model_fixedassets.id
        asset_account.multiple_assets_per_line = True

        vendor_bill_auto = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2020-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'account_id': asset_account.id,
                'name': 'Asus Laptop',
                'price_unit': 1000.0,
                'quantity': 2,
                'tax_ids': [Command.set(non_deductible_tax.ids)],
            })],
        })
        vendor_bill_auto.action_post()

        new_assets_auto = vendor_bill_auto.asset_ids
        self.assertEqual(len(new_assets_auto), 2)
        self.assertEqual(new_assets_auto.mapped('original_value'), [1105.0, 1105.0])
        self.assertEqual(new_assets_auto.mapped('non_deductible_tax_value'), [105.0, 105.0])

        # 2. Manual creation
        asset_account.create_asset = 'no'
        asset_account.asset_model = None
        asset_account.multiple_assets_per_line = False

        vendor_bill_manu = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2020-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'account_id': asset_account.id,
                    'name': 'Asus Laptop',
                    'price_unit': 1000.0,
                    'quantity': 2,
                    'tax_ids': [Command.set(non_deductible_tax.ids)]
                }),
                Command.create({
                    'account_id': asset_account.id,
                    'name': 'Lenovo Laptop',
                    'price_unit': 500.0,
                    'quantity': 3,
                    'tax_ids': [Command.set(non_deductible_tax.ids)]
                }),
            ],
        })
        vendor_bill_manu.action_post()

        # TOFIX: somewhere above this the field account.asset.asset_type is made
        # dirty, but this field has to be flushed in a specific environment.
        # This is because the field 'asset_type' is stored, computed and
        # context-dependent, which explains why its value must be retrieved
        # from the right environment.
        self.env.flush_all()

        move_line_ids = vendor_bill_manu.mapped('line_ids').filtered(lambda x: 'Laptop' in x.name)
        asset_form = Form(self.env['account.asset'].with_context(
            default_original_move_line_ids=move_line_ids.ids,
        ))
        asset_form.original_move_line_ids = move_line_ids
        asset_form.account_depreciation_expense_id = self.company_data['default_account_expense']

        new_assets_manu = asset_form.save()
        self.assertEqual(len(new_assets_manu), 1)
        self.assertEqual(new_assets_manu.original_value, 3867.5)
        self.assertEqual(new_assets_manu.non_deductible_tax_value, 367.5)

    def test_asset_degressive_01(self):
        """ Check the computation of an asset with degressive method,
            start at middle of the year
        """
        asset = self.env['account.asset'].create({
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'name': 'Degressive',
            'acquisition_date': '2021-07-01',
            'prorata_computation_type': 'constant_periods',
            'original_value': 10000,
            'method_number': 5,
            'method_period': '12',
            'method': 'degressive',
            'method_progress_factor': 0.5,
        })

        asset.validate()

        self.assertEqual(asset.method_number + 1, len(asset.depreciation_move_ids))

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)), [{
            'amount_total': 2500,
            'asset_remaining_value': 7500,
        }, {
            'amount_total': 3750,
            'asset_remaining_value': 3750,
        }, {
            'amount_total': 1875,
            'asset_remaining_value': 1875,
        }, {
            'amount_total': 937.5,
            'asset_remaining_value': 937.5,
        }, {
            'amount_total': 625.00,
            'asset_remaining_value': 312.50,
        }, {
            'amount_total': 312.50,
            'asset_remaining_value': 0,
        }])

    def test_asset_degressive_02(self):
        """ Check the computation of an asset with degressive method,
            start at beginning of the year.
        """
        asset = self.env['account.asset'].create({
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'name': 'Degressive',
            'acquisition_date': '2021-01-01',
            'original_value': 10000,
            'method_number': 5,
            'method_period': '12',
            'method': 'degressive',
            'method_progress_factor': 0.5,
        })

        asset.validate()

        self.assertEqual(asset.method_number, len(asset.depreciation_move_ids))

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)), [{
            'amount_total': 5000,
            'asset_remaining_value': 5000,
        }, {
            'amount_total': 2500,
            'asset_remaining_value': 2500,
        }, {
            'amount_total': 1250,
            'asset_remaining_value': 1250,
        }, {
            'amount_total': 625,
            'asset_remaining_value': 625,
        }, {
            'amount_total': 625,
            'asset_remaining_value': 0,
        }])

    def test_asset_negative_01(self):
        """ Check the computation of an asset with negative value. """
        asset = self.env['account.asset'].create({
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'name': 'Degressive Linear',
            'acquisition_date': '2021-07-01',
            'original_value': -10000,
            'method_number': 5,
            'method_period': '12',
            'method': 'linear',
        })
        asset.prorata_computation_type = 'constant_periods'

        asset.validate()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)), [{
            'amount_total': 1000,
            'asset_remaining_value': -9000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': -7000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': -5000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': -3000,
        }, {
            'amount_total': 2000,
            'asset_remaining_value': -1000,
        }, {
            'amount_total': 1000,
            'asset_remaining_value': 0,
        }])

    def test_asset_daily_computation_01(self):
        """ Check the computation of an asset with daily_computation. """
        asset = self.env['account.asset'].create({
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'name': 'Degressive Linear',
            'acquisition_date': '2021-07-01',
            'prorata_computation_type': 'daily_computation',
            'original_value': 10000,
            'method_number': 5,
            'method_period': '12',
            'method': 'linear',
        })

        asset.validate()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)), [{
            'amount_total': 1007.67,
            'asset_remaining_value': 8992.33,
        }, {
            'amount_total': 1998.90,
            'asset_remaining_value': 6993.43,
        }, {
            'amount_total': 1998.91,
            'asset_remaining_value': 4994.52,
        }, {
            'amount_total': 2004.38,
            'asset_remaining_value': 2990.14,
        }, {
            'amount_total': 1998.90,
            'asset_remaining_value': 991.24,
        }, {
            'amount_total': 991.24,
            'asset_remaining_value': 0,
        }])

    def test_decrement_book_value_with_negative_asset(self):
        """
        Test the computation of book value and remaining value
        when posting a depreciation move related with a negative asset
        """
        depreciation_account = self.company_data['default_account_assets'].copy()
        asset_model = self.env['account.asset'].create({
            'name': 'test',
            'state': 'model',
            'active': True,
            'method': 'linear',
            'method_number': 5,
            'method_period': '1',
            'prorata_computation_type': 'constant_periods',
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': depreciation_account.id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_purchase'].id,
        })

        depreciation_account.can_create_asset = True
        depreciation_account.create_asset = 'draft'
        depreciation_account.asset_model = asset_model

        refund = self.env['account.move'].create({
            'move_type': 'in_refund',
            'partner_id': self.partner_a.id,
            'invoice_date': '2021-06-01',
            'invoice_line_ids': [Command.create({'name': 'refund', 'account_id': depreciation_account.id, 'price_unit': 500, 'tax_ids': False})],
        })
        refund.action_post()

        self.assertTrue(refund.asset_ids)

        asset = refund.asset_ids

        self.assertEqual(asset.book_value, -refund.amount_total)
        self.assertEqual(asset.value_residual, -refund.amount_total)

        asset.validate()

        self.assertEqual(len(asset.depreciation_move_ids.filtered(lambda m: m.state == 'posted')), 1)
        self.assertEqual(asset.book_value, -400.0)
        self.assertEqual(asset.value_residual, -400.0)

    def test_depreciation_schedule_report_with_negative_asset(self):
        """
        Test the computation of depreciation schedule with negative asset
        """
        asset = self.env['account.asset'].create({
            'name': 'test',
            'original_value': -500,
            'method': 'linear',
            'method_number': 5,
            'method_period': '1',
            'acquisition_date': fields.Date.today() + relativedelta(months=-1),
            'prorata_computation_type': 'none',
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
        })

        asset.validate()

        report = self.env.ref('account_asset.assets_report')

        options = self._generate_options(report, fields.Date.today() + relativedelta(months=-7, day=1), fields.Date.today() + relativedelta(months=-6, day=31))

        expected_values_open_asset = [
            ("test", 0, 0, 500.0, -500.0, 0, 0, 100.0, -100.0, -400.0),
        ]

        self.assertLinesValues(report._get_lines(options)[2:3], [0, 5, 6, 7, 8, 9, 10, 11, 12, 13], expected_values_open_asset, options)

        expense_account_copy = self.company_data['default_account_expense'].copy()

        disposal_action_view = self.env['asset.modify'].create({
            'asset_id': asset.id,
            'modify_action': 'dispose',
            'loss_account_id': expense_account_copy.id,
            'date': fields.Date.today()
        }).sell_dispose()

        self.env['account.move'].browse(disposal_action_view['res_id']).action_post()

        expected_values_closed_asset = [
            ("test", 0, 500.0, 500.0, 0, 0, 500.0, 500.0, 0, 0),
        ]
        options = self._generate_options(report, fields.Date.today() + relativedelta(months=-7, day=1), fields.Date.today())
        self.assertLinesValues(report._get_lines(options)[2:3], [0, 5, 6, 7, 8, 9, 10, 11, 12, 13], expected_values_closed_asset, options)

    def test_depreciation_schedule_hierarchy(self):
        # Remove previously existing assets.
        assets = self.env['account.asset'].search([
            ('company_id', '=', self.env.company.id),
            ('state', '!=', 'model'),
        ])
        assets.state = 'draft'
        assets.mapped('depreciation_move_ids').state = 'draft'
        assets.unlink()

        # Create the account groups.
        self.env['account.group'].create([
            {'name': 'Group 1', 'code_prefix_start': '1', 'code_prefix_end': '1'},
            {'name': 'Group 11', 'code_prefix_start': '11', 'code_prefix_end': '11'},
            {'name': 'Group 12', 'code_prefix_start': '12', 'code_prefix_end': '12'},
        ])

        # Create the accounts.
        account_a, account_a1, account_b, account_c, account_d, account_e = self.env['account.account'].create([
            {'code': '1100', 'name': 'Account A', 'account_type': 'asset_non_current'},
            {'code': '1110', 'name': 'Account A1', 'account_type': 'asset_non_current'},
            {'code': '1200', 'name': 'Account B', 'account_type': 'asset_non_current'},
            {'code': '1300', 'name': 'Account C', 'account_type': 'asset_non_current'},
            {'code': '1400', 'name': 'Account D', 'account_type': 'asset_non_current'},
            {'code': '9999', 'name': 'Account E', 'account_type': 'asset_non_current'},
        ])

        # Create and validate the assets, and post the depreciation entries.
        self.env['account.asset'].create([
            {
                'account_asset_id': account_id,
                'account_depreciation_id': account_id,
                'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
                'journal_id': self.company_data['default_journal_misc'].id,
                'name': name,
                'acquisition_date': fields.Date.to_date('2020-07-01'),
                'original_value': original_value,
                'method': 'linear',
                'prorata_computation_type': 'none',
            }
            for account_id, name, original_value in [
                (account_a.id, 'ZenBook', 1250),
                (account_a.id, 'ThinkBook', 1500),
                (account_a1.id, 'XPS', 1750),
                (account_b.id, 'MacBook', 2000),
                (account_c.id, 'Aspire', 1600),
                (account_d.id, 'Playstation', 550),
                (account_e.id, 'Xbox', 500),
            ]
        ]).validate()

        # Configure the depreciation schedule report.
        report = self.env.ref('account_asset.assets_report')
        options = self._generate_options(report, '2022-01-01', '2022-12-31')
        options['hierarchy'] = True
        self.env.company.totals_below_sections = True

        # Generate and compare actual VS expected values.
        lines = [
            {
                'name': line['name'],
                'level': line['level'],
                'book_value': line['columns'][-1]['name']
            }
            for line in (report._get_lines(options))
        ]

        expected_values = [
            # pylint: disable=C0326
            {'name': '1 Group 1',                           'level': 1,     'book_value': '$\xa06,920.00'},
              {'name': '11 Group 11',                       'level': 2,     'book_value': '$\xa03,600.00'},
                {'name': '1100 Account A',                  'level': 3,     'book_value': '$\xa02,200.00'},
                  {'name': 'ZenBook',                       'level': 4,     'book_value': '$\xa01,000.00'},
                  {'name': 'ThinkBook',                     'level': 4,     'book_value': '$\xa01,200.00'},
                {'name': 'Total 1100 Account A',            'level': 3,     'book_value': '$\xa02,200.00'},
                {'name': '1110 Account A1',                 'level': 3,     'book_value': '$\xa01,400.00'},
                  {'name': 'XPS',                           'level': 4,     'book_value': '$\xa01,400.00'},
                {'name': 'Total 1110 Account A1',           'level': 3,     'book_value': '$\xa01,400.00'},
              {'name': 'Total 11 Group 11',                 'level': 2,     'book_value': '$\xa03,600.00'},
              {'name': '12 Group 12',                       'level': 2,     'book_value': '$\xa01,600.00'},
                {'name': '1200 Account B',                  'level': 3,     'book_value': '$\xa01,600.00'},
                  {'name': 'MacBook',                       'level': 4,     'book_value': '$\xa01,600.00'},
                {'name': 'Total 1200 Account B',            'level': 3,     'book_value': '$\xa01,600.00'},
              {'name': 'Total 12 Group 12',                 'level': 2,     'book_value': '$\xa01,600.00'},
              {'name': '1300 Account C',                    'level': 2,     'book_value': '$\xa01,280.00'},
                {'name': 'Aspire',                          'level': 3,     'book_value': '$\xa01,280.00'},
              {'name': 'Total 1300 Account C',              'level': 2,     'book_value': '$\xa01,280.00'},
              {'name': '1400 Account D',                    'level': 2,     'book_value': '$\xa0440.00'},
                {'name': 'Playstation',                     'level': 3,     'book_value': '$\xa0440.00'},
              {'name': 'Total 1400 Account D',              'level': 2,     'book_value': '$\xa0440.00'},
            {'name': 'Total 1 Group 1',                     'level': 1,     'book_value': '$\xa06,920.00'},
            {'name': '(No Group)',                          'level': 1,     'book_value': '$\xa0400.00'},
              {'name': '9999 Account E',                    'level': 2,     'book_value': '$\xa0400.00'},
                {'name': 'Xbox',                            'level': 3,     'book_value': '$\xa0400.00'},
              {'name': 'Total 9999 Account E',              'level': 2,     'book_value': '$\xa0400.00'},
            {'name': 'Total (No Group)',                    'level': 1,     'book_value': '$\xa0400.00'},
            {'name': 'Total',                               'level': 1,     'book_value': '$\xa07,320.00'},
        ]

        self.assertEqual(len(lines), len(expected_values))
        self.assertEqual(lines, expected_values)

    def test_depreciation_schedule_disposal_move_unposted(self):
        """
        Test the computation of values when disposing an asset, and the difference if the disposal move is posted
        """
        asset = self.env['account.asset'].create({
            'name': 'test asset',
            'method': 'linear',
            'original_value': 1000,
            'method_number': 5,
            'method_period': '12',
            'acquisition_date': fields.Date.today() + relativedelta(years=-2, month=1, day=1),
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
        })
        asset.validate()

        expense_account_copy = self.company_data['default_account_expense'].copy()

        disposal_action_view = self.env['asset.modify'].create({
            'asset_id': asset.id,
            'modify_action': 'dispose',
            'loss_account_id': expense_account_copy.id,
            'date': fields.Date.today() + relativedelta(days=-1)
        }).sell_dispose()

        report = self.env.ref('account_asset.assets_report')
        options = self._generate_options(report, '2021-01-01', '2021-12-31')

        # The disposal move is in draft and should not be considered (depreciation and book value)
        # Values are: name, assets_before, assets+, assets-, assets_after, depreciation_before, depreciation+, depreciation-, depreciation_after, book_value
        expected_values_asset_disposal_unposted = [
            ("test asset", 1000.0, 0.0, 0, 1000.0, 400.0, 100.0, 0.0, 500.0, 500.0),
        ]

        self.assertLinesValues(report._get_lines(options)[2:3], [0, 5, 6, 7, 8, 9, 10, 11, 12, 13], expected_values_asset_disposal_unposted, options)

        self.env['account.move'].browse(disposal_action_view.get('res_id')).action_post()

        expected_values_asset_disposal_posted = [
            ("test asset", 1000.0, 0.0, 1000.0, 0.0, 400.0, 100.0, 500.0, 0.0, 0.0),
        ]

        self.assertLinesValues(report._get_lines(options)[2:3], [0, 5, 6, 7, 8, 9, 10, 11, 12, 13], expected_values_asset_disposal_posted, options)

    def test_depreciation_schedule_disposal_move_unposted_with_non_depreciable_value(self):
        """
        Test the computation of values when disposing an asset with non-depreciable value, and the difference if the disposal move is posted
        """
        asset = self.env['account.asset'].create({
            'name': 'test asset',
            'method': 'linear',
            'original_value': 10000,
            'salvage_value': 8000,
            'method_number': 24,
            'method_period': '1',
            'acquisition_date': fields.Date.today() + relativedelta(months=-1, day=1),
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
        })
        asset.validate()

        report = self.env.ref('account_asset.assets_report')

        options = self._generate_options(report, '2021-07-01', '2021-07-31')

        expected_values_asset_disposal_unposted = [
            ("test asset", 10000.0, 0.0, 0.0, 10000.0, 83.33, 0.0, 0.0, 83.33, 9916.67),
        ]

        self.assertLinesValues(report._get_lines(options)[2:3], [0, 5, 6, 7, 8, 9, 10, 11, 12, 13], expected_values_asset_disposal_unposted, options)

        expense_account_copy = self.company_data['default_account_expense'].copy()

        disposal_action_view = self.env['asset.modify'].create({
            'asset_id': asset.id,
            'modify_action': 'dispose',
            'loss_account_id': expense_account_copy.id,
            'date': fields.Date.today()
        }).sell_dispose()

        expected_values_asset_disposal_unposted = [
            ("test asset", 10000.0, 0.0, 0.0, 10000.0, 83.33, 2.69, 0.0, 86.02, 9913.98),
        ]

        self.assertLinesValues(report._get_lines(options)[2:3], [0, 5, 6, 7, 8, 9, 10, 11, 12, 13], expected_values_asset_disposal_unposted, options)

        self.env['account.move'].browse(disposal_action_view['res_id']).action_post()

        expected_values_asset_disposal_posted = [
            ("test asset", 10000.0, 0.0, 10000.0, 0.0, 83.33, 2.69, 86.02, 0.0, 0.0),
        ]

        self.assertLinesValues(report._get_lines(options)[2:3], [0, 5, 6, 7, 8, 9, 10, 11, 12, 13], expected_values_asset_disposal_posted, options)

    def test_asset_analytic_on_lines(self):
        CEO_car = self.env['account.asset'].create({
            'salvage_value': 2000.0,
            'state': 'open',
            'method_period': '12',
            'method_number': 5,
            'name': "CEO's Car",
            'original_value': 12000.0,
            'model_id': self.account_asset_model_fixedassets.id,
            'acquisition_date': '2020-01-01',
        })
        CEO_car._onchange_model_id()
        CEO_car.method_number = 5
        CEO_car.analytic_distribution = {self.analytic_account.id: 100}

        # In order to test the process of Account Asset, I perform a action to confirm Account Asset.
        CEO_car.validate()

        for move in CEO_car.depreciation_move_ids:
            self.assertRecordValues(move.line_ids, [
                {
                    'analytic_distribution': {str(self.analytic_account.id): 100},
                },
                {
                    'analytic_distribution': {str(self.analytic_account.id): 100},
                },
            ])

        CEO_car.analytic_distribution = {str(self.analytic_account.id): 200}

        # Only draft moves should have a changed analytic distribution
        for move in CEO_car.depreciation_move_ids.filtered(lambda m: m.state == 'posted'):
            self.assertRecordValues(move.line_ids, [
                {
                    'analytic_distribution': {str(self.analytic_account.id): 100},
                },
                {
                    'analytic_distribution': {str(self.analytic_account.id): 100},
                },
            ])

        for move in CEO_car.depreciation_move_ids.filtered(lambda m: m.state == 'draft'):
            self.assertRecordValues(move.line_ids, [
                {
                    'analytic_distribution': {str(self.analytic_account.id): 200},
                },
                {
                    'analytic_distribution': {str(self.analytic_account.id): 200},
                },
            ])


    def test_asset_analytic_filter(self):
        """
        Test that the analytic filter works correctly.
        """
        truck_b = self.truck.copy()
        truck_b.acquisition_date = self.truck.acquisition_date
        truck_b.validate()
        self.truck.analytic_distribution = {self.analytic_account.id: 100}
        self.env['account.move']._autopost_draft_entries()

        self.env.company.totals_below_sections = False
        report = self.env.ref('account_asset.assets_report')

        # No prefix group, no group by account
        options = self._generate_options(report, '2021-01-01', '2021-12-31', default_options={'assets_groupby_account': False, 'unfold_all': False})

        # without Analytic Filter
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #    Name                       Assets/start  Assets/+  Assets/- Assets/end  Depreciation/start  Depreciation/+  Depreciation/- Depreciation/end  Book Value
            [    0,                             5,        6,        7,           8,          9,              10,             11,               12,               13],
            [
                ('truck',                   10000,        0,        0,       10000,       4500,               0,              0,             4500,             5500,),
                ('truck (copy)',            10000,        0,        0,       10000,       4500,               0,              0,             4500,             5500,),
                ('Total',                   20000,        0,        0,       20000,       9000,               0,              0,             9000,            11000,),
            ],
            options
        )
        # with Analytic Filter
        options['analytic_accounts'] = [self.analytic_account.id]
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #    Name                       Assets/start  Assets/+  Assets/- Assets/end  Depreciation/start  Depreciation/+  Depreciation/- Depreciation/end  Book Value
            [    0,                             5,        6,        7,           8,          9,              10,             11,               12,               13],
            [
                ('truck',                   10000,        0,        0,       10000,       4500,               0,              0,             4500,             5500,),
                ('Total',                   10000,        0,        0,       10000,       4500,               0,              0,             4500,             5500,),
            ],
            options
        )

    def test_asset_analytic_groupby(self):
        """
        Test that the analytic groupby works correctly.
        """
        truck_b = self.truck.copy()
        truck_b.acquisition_date = self.truck.acquisition_date
        truck_b.validate()
        self.truck.analytic_distribution = {self.analytic_account.id: 100}
        self.env['account.move']._autopost_draft_entries()

        self.env.company.totals_below_sections = False
        report = self.env.ref('account_asset.assets_report')
        report.filter_analytic_groupby = True

        # No prefix group, no group by account
        options = self._generate_options(report, '2021-01-01', '2021-12-31', default_options={'assets_groupby_account': False, 'unfold_all': False})

        # without Analytic Groupby
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #    Name                       Assets/start  Assets/+  Assets/- Assets/end  Depreciation/start  Depreciation/+  Depreciation/- Depreciation/end  Book Value
            [    0,                             5,        6,        7,           8,          9,              10,             11,               12,               13],
            [
                ('truck',                   10000,        0,        0,       10000,       4500,               0,              0,             4500,             5500,),
                ('truck (copy)',            10000,        0,        0,       10000,       4500,               0,              0,             4500,             5500,),
                ('Total',                   20000,        0,        0,       20000,       9000,               0,              0,             9000,            11000,),
            ],
            options
        )
        # with Analytic Groupby
        options = self._generate_options(report, '2021-01-01', '2021-12-31', default_options={
            'assets_groupby_account': False,
            'unfold_all': False,
            'analytic_accounts_groupby': [self.analytic_account.id],
        })
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #    Group                      |                                            ANALYTIC                                                                       |  |                                                    ALL                                                                               |
            #    Name                       Assets/start  Assets/+  Assets/- Assets/end  Depreciation/start  Depreciation/+  Depreciation/- Depreciation/end  Book Value    Assets/start    Assets/+    Assets/-    Assets/end  Depreciation/start  Depreciation/+  Depreciation/-  Depreciation/end    Book Value
            [    0,                             5,        6,        7,           8,          9,              10,             11,               12,               13,            18,         19,         20,             21,         22,             23,             24,             25,                 26],
            [
                ('truck',                   10000,        0,        0,       10000,       4500,               0,              0,             4500,             5500,         10000,         0,          0,          10000,        4500,              0,             0,            4500,               5500),
                ('truck (copy)',               '',       '',       '',          '',         '',              '',             '',               '',               '',         10000,         0,          0,          10000,        4500,              0,             0,            4500,               5500),
                ('Total',                   10000,        0,        0,       10000,       4500,               0,              0,             4500,             5500,         20000,         0,          0,          20000,        9000,              0,             0,            9000,              11000),
            ],
            options
        )

    def test_depreciation_schedule_report_first_depreciation(self):
        """Test that the depreciation schedule report displays the correct first depreciation date."""
        # check that the truck's first depreciation date is correct:
        # the truck has a yearly linear depreciation and it's prorate_date is 2015-01-01
        # therefore we expect it's first depreciation date to be the last day of 2015

        today = fields.Date.today()
        report = self.env.ref('account_asset.assets_report')
        options = self._generate_options(report, today + relativedelta(years=-6, month=1, day=1), today + relativedelta(years=+4, month=12, day=31))
        lines = report._get_lines({**options, **{'unfold_all': False, 'all_entries': True}})

        self.assertEqual(lines[1]['columns'][1]['name'], '12/31/2015')

    def test_asset_modify_sell_multicurrency(self):
        """ Test that the closing invoice's currency is taken into account when selling an asset. """
        closing_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'price_unit': 5000})]
        })
        self.env['asset.modify'].create({
            'asset_id': self.truck.id,
            'invoice_line_ids': closing_invoice.invoice_line_ids,
            'date': fields.Date.today() + relativedelta(months=-6, days=-1),
            'modify_action': 'sell',
        }).sell_dispose()

        closing_move = self.truck.depreciation_move_ids.filtered(lambda l: l.state == 'draft')

        self.assertRecordValues(closing_move.line_ids, [{
            'debit': 0,
            'credit': 10000,
            'account_id': self.truck.account_asset_id.id,
        }, {
            'debit': 4500,
            'credit': 0,
            'account_id': self.truck.account_depreciation_id.id,
        }, {
            'debit': 2500,
            'credit': 0,
            'account_id': closing_invoice.invoice_line_ids.account_id.id,
        }, {
            'debit': 3000,
            'credit': 0,
            'account_id': self.env.company.loss_account_id.id,
        }])

    def test_depreciation_schedule_prefix_groups(self):
        for i in range(1, 3):
            asset = self.env['account.asset'].create({
                'method_period': '12',
                'method_number': 4,
                'name': f"Asset {i}",
                'original_value': i * 100.0,
                'acquisition_date': fields.Date.today() - relativedelta(years=3),
                'account_asset_id': self.company_data['default_account_assets'].id,
                'account_depreciation_id': self.company_data['default_account_assets'].copy().id,
                'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
                'journal_id': self.company_data['default_journal_misc'].id,
                'prorata_computation_type': 'none',
            })
            asset.validate()

        self.env['account.move']._autopost_draft_entries()

        self.env.company.totals_below_sections = False
        report = self.env.ref('account_asset.assets_report')

        # No prefix group, no group by account
        options = self._generate_options(report, '2021-01-01', '2021-12-31', default_options={'assets_groupby_account': False})
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #    Name                       Assets/start  Assets/+  Assets/- Assets/end  Depreciation/start  Depreciation/+  Depreciation/- Depreciation/end  Book Value
            [    0,                         5,            6,        7,       8,          9,                  10,             11,            12,               13],
            [
                ('truck',                   10000,       0,       0,       10000,      4500,               0,             0,            4500,             5500,),
                ('Asset 1',                   100,       0,       0,         100,        75,               0,             0,              75,               25,),
                ('Asset 2',                   200,       0,       0,         200,       150,               0,             0,             150,               50,),
                ('Total',                   10300,       0,       0,       10300,      4725,               0,             0,            4725,             5575,),
            ],
            options,
        )

        # No prefix group, group by account
        options = self._generate_options(report, '2021-01-01', '2021-12-31', default_options={'assets_groupby_account': True})
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #    Name                       Assets/start  Assets/+  Assets/- Assets/end  Depreciation/start  Depreciation/+  Depreciation/- Depreciation/end  Book Value
        [    0,                                 5,              6,        7,       8,          9,                  10,             11,            12,               13],
            [
                ('151000 Fixed Asset',          10300,          0,       0,       10300,      4725,               0,             0,            4725,             5575,),
                ('truck',                       10000,          0,       0,       10000,      4500,               0,             0,            4500,             5500,),
                ('Asset 1',                     100,            0,       0,         100,        75,               0,             0,              75,               25,),
                ('Asset 2',                     200,            0,       0,         200,       150,               0,             0,             150,               50,),
                ('Total',                       10300,          0,       0,       10300,      4725,               0,             0,            4725,             5575,),
            ],
            options,
        )

        report.prefix_groups_threshold = 3
        # Prefix group, no group by account
        options = self._generate_options(report, '2021-01-01', '2021-12-31', default_options={'assets_groupby_account': False, 'unfold_all': True})
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #    Name                       Assets/start  Assets/+  Assets/- Assets/end  Depreciation/start  Depreciation/+  Depreciation/- Depreciation/end  Book Value
            [    0,                         5,            6,        7,       8,          9,                  10,             11,            12,               13],
            [
                ('A (2 lines)',               300,       0,       0,         300,       225,               0,             0,             225,               75,),
                ('Asset 1',                   100,       0,       0,         100,        75,               0,             0,              75,               25,),
                ('Asset 2',                   200,       0,       0,         200,       150,               0,             0,             150,               50,),
                ('T (1 line)',              10000,       0,       0,       10000,      4500,               0,             0,            4500,             5500,),
                ('truck',                   10000,       0,       0,       10000,      4500,               0,             0,            4500,             5500,),
                ('Total',                   10300,       0,       0,       10300,      4725,               0,             0,            4725,             5575,),
            ],
            options,
        )

        # Prefix group, group by account
        options = self._generate_options(report, '2021-01-01', '2021-12-31', default_options={'assets_groupby_account': True, 'unfold_all': True})
        options['unfold_all'] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            report._get_lines(options),
            #    Name                       Assets/start  Assets/+  Assets/- Assets/end  Depreciation/start  Depreciation/+  Depreciation/- Depreciation/end  Book Value
            [    0,                             5,              6,        7,       8,          9,                  10,             11,            12,               13],
            [
                ('151000 Fixed Asset',          10300,          0,       0,       10300,      4725,               0,             0,            4725,             5575,),
                ('A (2 lines)',                 300,            0,       0,         300,       225,               0,             0,             225,               75,),
                ('Asset 1',                     100,            0,       0,         100,        75,               0,             0,              75,               25,),
                ('Asset 2',                     200,            0,       0,         200,       150,               0,             0,             150,               50,),
                ('T (1 line)',                  10000,          0,       0,       10000,      4500,               0,             0,            4500,             5500,),
                ('truck',                       10000,          0,       0,       10000,      4500,               0,             0,            4500,             5500,),
                ('Total',                       10300,          0,       0,       10300,      4725,               0,             0,            4725,             5575,),
            ],
            options,
        )

    def test_archive_asset_model(self):
        """ Test that we can archive an asset model. """
        self.account_asset_model_fixedassets.active = False
        self.assertFalse(self.account_asset_model_fixedassets.active)

    def test_asset_increase_with_lock_year(self):
        """ Test the dates at which the moves are posted even with increase, with lock date"""
        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2021-03-01')

        asset = self.env['account.asset'].create({
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'name': 'Car',
            'acquisition_date': fields.Date.today() + relativedelta(months=-6),
            'original_value': 12000,
            'method_number': 12,
            'method_period': '1',
            'method': 'linear',
        })

        asset.validate()

        self.assertRecordValues(
            asset.depreciation_move_ids.sorted(lambda l: (l.date, l.id)),
            [
                {'date': fields.Date.to_date('2021-03-31')},
                {'date': fields.Date.to_date('2021-03-31')},
                {'date': fields.Date.to_date('2021-03-31')},
                {'date': fields.Date.to_date('2021-04-30')},
                {'date': fields.Date.to_date('2021-05-31')},
                {'date': fields.Date.to_date('2021-06-30')},
                {'date': fields.Date.to_date('2021-07-31')},
                {'date': fields.Date.to_date('2021-08-31')},
                {'date': fields.Date.to_date('2021-09-30')},
                {'date': fields.Date.to_date('2021-10-31')},
                {'date': fields.Date.to_date('2021-11-30')},
                {'date': fields.Date.to_date('2021-12-31')}
            ]
        )

        self.assertEqual(asset.book_value, 6000)

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test increase with lock date',
            'value_residual': 8000.0,
            'date':  fields.Date.today() + relativedelta(days=-1),
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        self.assertEqual(asset.book_value, 8000)

        self.assertRecordValues(
            asset.children_ids.depreciation_move_ids.sorted(lambda dep: (dep.date, dep.id)),
            [
                {'date': fields.Date.to_date('2021-07-31'), 'depreciation_value': 333.33},
                {'date': fields.Date.to_date('2021-08-31'), 'depreciation_value': 333.34},
                {'date': fields.Date.to_date('2021-09-30'), 'depreciation_value': 333.33},
                {'date': fields.Date.to_date('2021-10-31'), 'depreciation_value': 333.33},
                {'date': fields.Date.to_date('2021-11-30'), 'depreciation_value': 333.34},
                {'date': fields.Date.to_date('2021-12-31'), 'depreciation_value': 333.33}
            ]
        )

    def test_asset_decrease_with_lock_year(self):
        """ Test the dates and values for the moves that are posted with decrease and lock date"""
        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2021-03-01')

        asset = self.env['account.asset'].create({
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'name': 'Car',
            'acquisition_date': fields.Date.today() + relativedelta(months=-6),
            'original_value': 12000,
            'method_number': 12,
            'method_period': '1',
            'method': 'linear',
        })

        asset.validate()

        self.assertEqual(asset.book_value, 6000)

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test decrease with lock date',
            'value_residual': 4000.0,
            'date':  fields.Date.today() + relativedelta(days=-1),
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        self.assertEqual(asset.book_value, 4000)

        self.assertRecordValues(
            asset.depreciation_move_ids.sorted(lambda dep: (dep.date, dep.id)),
            [
                {'date': fields.Date.to_date('2021-03-31'), 'depreciation_value': 1000},
                {'date': fields.Date.to_date('2021-03-31'), 'depreciation_value': 1000},
                {'date': fields.Date.to_date('2021-03-31'), 'depreciation_value': 1000},
                {'date': fields.Date.to_date('2021-04-30'), 'depreciation_value': 1000},
                {'date': fields.Date.to_date('2021-05-31'), 'depreciation_value': 1000},
                {'date': fields.Date.to_date('2021-06-30'), 'depreciation_value': 1000},
                {'date': fields.Date.to_date('2021-06-30'), 'depreciation_value': 2000},
                {'date': fields.Date.to_date('2021-07-31'), 'depreciation_value': 666.67},
                {'date': fields.Date.to_date('2021-08-31'), 'depreciation_value': 666.66},
                {'date': fields.Date.to_date('2021-09-30'), 'depreciation_value': 666.67},
                {'date': fields.Date.to_date('2021-10-31'), 'depreciation_value': 666.67},
                {'date': fields.Date.to_date('2021-11-30'), 'depreciation_value': 666.66},
                {'date': fields.Date.to_date('2021-12-31'), 'depreciation_value': 666.67}
            ]
        )

    def test_asset_onchange_model(self):
        """
        Test the changes of account_asset_id when changing asset models
        """
        account_asset = self.company_data['default_account_assets'].copy()
        asset_model = self.env['account.asset'].create({
            'name': 'test model',
            'state': 'model',
            'active': True,
            'method': 'linear',
            'method_number': 5,
            'method_period': '1',
            'prorata_computation_type': 'none',
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'account_asset_id': account_asset.id,
            'journal_id': self.company_data['default_journal_misc'].id,
        })

        asset_model_with_account = self.env['account.asset'].create({
            'name': 'test model with account',
            'state': 'model',
            'active': True,
            'method': 'linear',
            'method_number': 5,
            'method_period': '1',
            'prorata_computation_type': 'none',
            'account_depreciation_id': self.company_data['default_account_assets'].id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
        })

        asset_form = Form(self.env['account.asset'])
        asset_form.name = "Test Asset"
        asset_form.original_value = 10000
        asset_form.model_id = asset_model

        self.assertEqual(asset_form.account_asset_id, account_asset, "The account_asset_id should be the one from the model")

        asset_form.model_id = asset_model_with_account
        self.assertEqual(asset_form.account_asset_id, self.company_data['default_account_assets'], "The account_asset_id should be computed from the depreciation account from the model")

        other_account_on_bill = self.company_data['default_account_assets'].copy()
        other_account_on_bill.create_asset = 'draft'
        other_account_on_bill.asset_model = asset_model
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2020-12-31',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'A beautiful small bomb',
                    'account_id': other_account_on_bill.id,
                    'price_unit': 200.0,
                    'quantity': 1,
                }),
            ],
        })
        invoice.action_post()

        self.assertEqual(invoice.asset_ids.account_asset_id, other_account_on_bill,
                         "The account should be the one from the bill, not the model")

        asset_form = Form(invoice.asset_ids)
        asset_form.model_id = asset_model

        self.assertEqual(asset_form.account_asset_id, other_account_on_bill, "We keep the account from the bill")

    def test_asset_reevaluation_degressive_linear(self):
        """ Tests the reevaluation of an asset in degressive_then_linear with a gross increase"""
        asset = self.env['account.asset'].create({
            'method_period': '12',
            'method_number': 5,
            'name': "Car with purple sticker",
            'original_value': 10000.0,
            'acquisition_date': fields.Date.today() - relativedelta(years=2),
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'prorata_computation_type': 'none',
            'method': 'degressive_then_linear',
            'method_progress_factor': 0.4,
        })
        asset.validate()
        self.assertRecordValues(asset.depreciation_move_ids, [{
            'depreciation_value': 4000,
            'asset_remaining_value': 6000,
            'state': 'posted',
        }, {
            'depreciation_value': 2400,
            'asset_remaining_value': 3600,
            'state': 'posted',
        }, {
            'depreciation_value': 2000,
            'asset_remaining_value': 1600,
            'state': 'draft',
        }, {
            'depreciation_value': 1600,
            'asset_remaining_value': 0,
            'state': 'draft',
        }])
        self.env['asset.modify'].create({
            'name': "Inflation made it take 20%!",
            'date': fields.Date.today() + relativedelta(months=-6, days=-1),
            'asset_id': asset.id,
            'value_residual': 5600,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()
        self.assertRecordValues(asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [{
            # (2000 + 2000*6400/3600) / 5
            'depreciation_value': 1111.11,
            'asset_remaining_value': 888.89,
            'state': 'draft',
        }, {
            'depreciation_value': 888.89,
            'asset_remaining_value': 0,
            'state': 'draft',
        }])

    def test_asset_already_depreciated(self):
        asset = self.env['account.asset'].create({
            'method_period': '12',
            'method_number': 5,
            'name': "Car with purple sticker",
            'original_value': 10000.0,
            'acquisition_date': fields.Date.today() - relativedelta(years=1),
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'prorata_computation_type': 'none',
            'already_depreciated_amount_import': 3000,
        })
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'date': fields.Date.today() - relativedelta(days=1),
            'name': 'Test reason',
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids, [{
            'depreciation_value': 1000,
            'date': fields.Date.to_date('2021-12-31'),
        }, {
            'depreciation_value': 2000,
            'date': fields.Date.to_date('2022-12-31'),
        }, {
            'depreciation_value': 2000,
            'date': fields.Date.to_date('2023-12-31'),
        }, {
            'depreciation_value': 2000,
            'date': fields.Date.to_date('2024-12-31'),
        },
        ])

        fully_depreciated_asset = self.env['account.asset'].create({
            'method_period': '12',
            'method_number': 5,
            'name': "Car with purple sticker",
            'original_value': 10000.0,
            'acquisition_date': fields.Date.today() - relativedelta(years=2),
            'account_asset_id': self.company_data['default_account_assets'].id,
            'account_depreciation_id': self.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': self.company_data['default_account_expense'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'prorata_computation_type': 'none',
            'salvage_value': 4000,
            'already_depreciated_amount_import': 6000,
        })
        fully_depreciated_asset.validate()

        self.env['asset.modify'].create({
            'asset_id': fully_depreciated_asset.id,
            'date': fields.Date.today(),
            'modify_action': 'dispose',
        }).sell_dispose()
        self.assertEqual(len(fully_depreciated_asset.depreciation_move_ids), 1, "Only the disposal should be created")
