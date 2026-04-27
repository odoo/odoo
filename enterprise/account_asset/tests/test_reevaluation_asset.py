from unittest.mock import patch
from odoo.tests.common import tagged, freeze_time
from odoo.addons.account_asset.tests.common import TestAccountAssetCommon
from odoo import fields


@freeze_time('2022-06-30')
@tagged('post_install', '-at_install')
class TestAccountAssetReevaluation(TestAccountAssetCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_depreciation_expense = cls.company_data['default_account_assets'].copy()
        cls.asset_counterpart_account_id = cls.company_data['default_account_expense'].copy()
        cls.degressive_asset = cls.create_asset(
            value=7200,
            periodicity="monthly",
            periods=60,
            method="degressive",
            method_progress_factor=0.35,
            acquisition_date="2020-07-01",
            prorata_computation_type="constant_periods"
        )
        cls.degressive_then_linear_asset = cls.create_asset(
            value=7200,
            periodicity="monthly",
            periods=60,
            method="degressive_then_linear",
            method_progress_factor=0.35,
            acquisition_date="2020-07-01",
            prorata_computation_type="constant_periods"
        )

    def test_linear_start_beginning_month_reevaluation_beginning_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-01", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-01"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=600, remaining_value=6600, depreciated_value=600, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6000, depreciated_value=1200, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5400, depreciated_value=1800, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=4800, depreciated_value=2400, state='posted'),
            # 20 because we have 1 * 600 / 30 (1 day of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-01', depreciation_value=20, remaining_value=4780, depreciated_value=2420, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=580, remaining_value=4200, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3600, depreciated_value=3600, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3000, depreciated_value=4200, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2400, depreciated_value=4800, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=1800, depreciated_value=5400, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1200, depreciated_value=6000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=600, depreciated_value=6600, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_beginning_month_reevaluation_middle_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-01", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-15")
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=600, remaining_value=6600, depreciated_value=600, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6000, depreciated_value=1200, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5400, depreciated_value=1800, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=4800, depreciated_value=2400, state='posted'),
            # 300 because we have 15 * 600 / 30 (15 days of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=300, remaining_value=4500, depreciated_value=2700, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=300, remaining_value=4200, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3600, depreciated_value=3600, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3000, depreciated_value=4200, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2400, depreciated_value=4800, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=1800, depreciated_value=5400, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1200, depreciated_value=6000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=600, depreciated_value=6600, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_beginning_month_reevaluation_end_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-01", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30")
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=600, remaining_value=6600, depreciated_value=600, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6000, depreciated_value=1200, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5400, depreciated_value=1800, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=4800, depreciated_value=2400, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=600, remaining_value=4200, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3600, depreciated_value=3600, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3000, depreciated_value=4200, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2400, depreciated_value=4800, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=1800, depreciated_value=5400, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1200, depreciated_value=6000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=600, depreciated_value=6600, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_middle_month_reevaluation_beginning_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-15", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-01"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=300, remaining_value=6900, depreciated_value=300, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6300, depreciated_value=900, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5700, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5100, depreciated_value=2100, state='posted'),
            # 20 because we have 1 * 600 / 30 (1 day of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-01', depreciation_value=20, remaining_value=5080, depreciated_value=2120, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=580, remaining_value=4500, depreciated_value=2700, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3900, depreciated_value=3300, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3300, depreciated_value=3900, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2700, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2100, depreciated_value=5100, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1500, depreciated_value=5700, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=900, depreciated_value=6300, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=300, depreciated_value=6900, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=300, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_middle_month_reevaluation_middle_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-15", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-15"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=300, remaining_value=6900, depreciated_value=300, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6300, depreciated_value=900, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5700, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5100, depreciated_value=2100, state='posted'),
            # 300 because we have 15 * 600 / 30 (15 days of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=300, remaining_value=4800, depreciated_value=2400, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=300, remaining_value=4500, depreciated_value=2700, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3900, depreciated_value=3300, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3300, depreciated_value=3900, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2700, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2100, depreciated_value=5100, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1500, depreciated_value=5700, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=900, depreciated_value=6300, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=300, depreciated_value=6900, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=300, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_middle_month_reevaluation_end_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-15", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=300, remaining_value=6900, depreciated_value=300, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6300, depreciated_value=900, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5700, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5100, depreciated_value=2100, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=600, remaining_value=4500, depreciated_value=2700, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3900, depreciated_value=3300, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3300, depreciated_value=3900, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2700, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2100, depreciated_value=5100, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1500, depreciated_value=5700, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=900, depreciated_value=6300, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=300, depreciated_value=6900, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=300, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_end_month_reevaluation_beginning_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-28", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-01"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=21.43, remaining_value=7178.57, depreciated_value=21.43, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6578.57, depreciated_value=621.43, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5978.57, depreciated_value=1221.43, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5378.57, depreciated_value=1821.43, state='posted'),
            # 20 because we have 1 * 600 / 30 (1 day of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-01', depreciation_value=20, remaining_value=5358.57, depreciated_value=1841.43, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=580, remaining_value=4778.57, depreciated_value=2421.43, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=4178.57, depreciated_value=3021.43, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3578.57, depreciated_value=3621.43, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2978.57, depreciated_value=4221.43, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2378.57, depreciated_value=4821.43, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1778.57, depreciated_value=5421.43, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=1178.57, depreciated_value=6021.43, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=578.57, depreciated_value=6621.43, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=578.57, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_end_month_reevaluation_middle_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-28", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-15"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=21.43, remaining_value=7178.57, depreciated_value=21.43, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6578.57, depreciated_value=621.43, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5978.57, depreciated_value=1221.43, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5378.57, depreciated_value=1821.43, state='posted'),
            # 300 because we have 15 * 600 / 30 (15 days of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=300, remaining_value=5078.57, depreciated_value=2121.43, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=300, remaining_value=4778.57, depreciated_value=2421.43, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=4178.57, depreciated_value=3021.43, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3578.57, depreciated_value=3621.43, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2978.57, depreciated_value=4221.43, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2378.57, depreciated_value=4821.43, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1778.57, depreciated_value=5421.43, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=1178.57, depreciated_value=6021.43, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=578.57, depreciated_value=6621.43, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=578.57, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_end_month_reevaluation_end_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-28", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=21.43, remaining_value=7178.57, depreciated_value=21.43, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6578.57, depreciated_value=621.43, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5978.57, depreciated_value=1221.43, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5378.57, depreciated_value=1821.43, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=600, remaining_value=4778.57, depreciated_value=2421.43, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=4178.57, depreciated_value=3021.43, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3578.57, depreciated_value=3621.43, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2978.57, depreciated_value=4221.43, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2378.57, depreciated_value=4821.43, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1778.57, depreciated_value=5421.43, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=1178.57, depreciated_value=6021.43, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=578.57, depreciated_value=6621.43, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=578.57, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_reevaluation_simple_decrease(self):
        asset = self.create_asset(value=10000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
            'value_residual': 4000,  # -1000
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=833.33, remaining_value=9166.67, depreciated_value=833.33, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=833.34, remaining_value=8333.33, depreciated_value=1666.67, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=833.33, remaining_value=7500, depreciated_value=2500, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=833.33, remaining_value=6666.67, depreciated_value=3333.33, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=833.34, remaining_value=5833.33, depreciated_value=4166.67, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=833.33, remaining_value=5000, depreciated_value=5000, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=4000, depreciated_value=6000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=666.67, remaining_value=3333.33, depreciated_value=6666.67, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=666.66, remaining_value=2666.67, depreciated_value=7333.33, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=666.67, remaining_value=2000, depreciated_value=8000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=666.67, remaining_value=1333.33, depreciated_value=8666.67, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=666.66, remaining_value=666.67, depreciated_value=9333.33, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=666.67, remaining_value=0, depreciated_value=10000, state='draft'),
        ])

    def test_linear_reevaluation_double_decrease(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        date_modify = fields.Date.to_date("2022-04-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'value_residual': asset._get_residual_value_at_date(date_modify) - 8500,
        }).modify()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
            'value_residual': 18000,  # -6000
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=8500, remaining_value=34000, depreciated_value=26000, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=4000, remaining_value=28000, depreciated_value=32000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=4000, remaining_value=24000, depreciated_value=36000, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=6000, remaining_value=18000, depreciated_value=42000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=3000, remaining_value=15000, depreciated_value=45000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=3000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=3000, remaining_value=9000, depreciated_value=51000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=3000, remaining_value=6000, depreciated_value=54000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=3000, remaining_value=3000, depreciated_value=57000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=3000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_reevaluation_double_increase(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        date_modify_1 = fields.Date.to_date("2022-04-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_1,
            'value_residual': asset._get_residual_value_at_date(date_modify_1) + 8500,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        date_modify_2 = fields.Date.to_date("2022-06-30")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_2,
            'value_residual': asset._get_residual_value_at_date(date_modify_2) + 6000,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2500, remaining_value=40000, depreciated_value=20000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=5000, remaining_value=35000, depreciated_value=25000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=5000, remaining_value=30000, depreciated_value=30000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=5000, remaining_value=25000, depreciated_value=35000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=5000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=5000, remaining_value=15000, depreciated_value=45000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=5000, remaining_value=10000, depreciated_value=50000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=5000, remaining_value=5000, depreciated_value=55000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=5000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=500, remaining_value=8000, depreciated_value=500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=7000, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=6000, depreciated_value=2500, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=3500, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=5500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=6500, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=7500, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=8500, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[1].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=1000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=2000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=3000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=4000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=5000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=6000, state='draft'),
        ])

    def test_linear_reevaluation_decrease_then_increase(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        date_modify_1 = fields.Date.to_date("2022-04-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_1,
            'value_residual': asset._get_residual_value_at_date(date_modify_1) - 8500,
        }).modify()

        date_modify_2 = fields.Date.to_date("2022-06-30")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_2,
            'value_residual': asset._get_residual_value_at_date(date_modify_2) + 6000,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=8500, remaining_value=34000, depreciated_value=26000, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=4000, remaining_value=28000, depreciated_value=32000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=4000, remaining_value=24000, depreciated_value=36000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=4000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=4000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=4000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=4000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=4000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=4000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=1000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=2000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=3000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=4000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=5000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=6000, state='draft'),
        ])

    def test_linear_reevaluation_increase_then_decrease_in_future(self):
        asset = self.create_asset(value=10000, periodicity="yearly", periods=5, method="linear", acquisition_date="2018-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        date_modify_1 = fields.Date.to_date("2022-06-30")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_1,
            'value_residual': asset._get_residual_value_at_date(date_modify_1) + 1000,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        date_modify_2 = fields.Date.to_date("2022-09-30")  # This is 3 month in the future
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_2,
            'value_residual': asset._get_residual_value_at_date(date_modify_2) - 200,
            'method_period': '1',  # to reflect the change on the child, we go in monthly
            'method_number': 60,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2018-12-31', depreciation_value=2000, remaining_value=8000, depreciated_value=2000, state='posted'),
            self._get_depreciation_move_values(date='2019-12-31', depreciation_value=2000, remaining_value=6000, depreciated_value=4000, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=2000, remaining_value=4000, depreciated_value=6000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=2000, remaining_value=2000, depreciated_value=8000, state='posted'),
            # move before increase
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=1000, depreciated_value=9000, state='posted'),
            # move before decrease
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=500, remaining_value=500, depreciated_value=9500, state='draft'),
            # decrease move
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=200, remaining_value=300, depreciated_value=9700, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=100, remaining_value=200, depreciated_value=9800, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=100, remaining_value=100, depreciated_value=9900, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=100, remaining_value=0, depreciated_value=10000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            # move before switch to monthly
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=500, remaining_value=500, depreciated_value=500, state='draft'),

            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=166.67, remaining_value=333.33, depreciated_value=666.67, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=166.66, remaining_value=166.67, depreciated_value=833.33, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=166.67, remaining_value=0, depreciated_value=1000, state='draft'),
        ])

    def test_linear_reevaluation_decrease_then_increase_with_lock_date(self):
        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2022-03-01')
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        date_modify_1 = fields.Date.to_date("2022-04-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_1,
            'value_residual': asset._get_residual_value_at_date(date_modify_1) - 8500,
        }).modify()

        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2022-05-01')

        date_modify_2 = fields.Date.to_date("2022-06-30")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_2,
            'value_residual': asset._get_residual_value_at_date(date_modify_2) + 6000,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=8500, remaining_value=34000, depreciated_value=26000, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=4000, remaining_value=28000, depreciated_value=32000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=4000, remaining_value=24000, depreciated_value=36000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=4000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=4000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=4000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=4000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=4000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=4000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=1000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=2000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=3000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=4000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=5000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=6000, state='draft'),
        ])

    def test_linear_reevaluation_increase_then_decrease(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        date_modify_1 = fields.Date.to_date("2022-04-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_1,
            'value_residual': asset._get_residual_value_at_date(date_modify_1) + 8500,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        date_modify_2 = fields.Date.to_date("2022-06-30")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify_2,
            'value_residual': asset._get_residual_value_at_date(date_modify_2) - 6000,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2500, remaining_value=40000, depreciated_value=20000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=5000, remaining_value=35000, depreciated_value=25000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=5000, remaining_value=30000, depreciated_value=30000, state='posted'),

            # decrease move
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=6000, remaining_value=24000, depreciated_value=36000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=4000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=4000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=4000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=4000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=4000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=4000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=500, remaining_value=8000, depreciated_value=500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=7000, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=6000, depreciated_value=2500, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=3500, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=5500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=6500, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=7500, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=8500, state='draft'),
        ])

    def test_linear_reevaluation_decrease_then_disposal(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata_computation_type="constant_periods")
        asset.validate()
        self.loss_account_id = self.company_data['default_account_expense'].copy().id

        date_modify = fields.Date.to_date("2022-04-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'value_residual': asset._get_residual_value_at_date(date_modify) - 8500,
        }).modify()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'date':  fields.Date.to_date("2022-06-30"),
            'modify_action': 'dispose',
            'loss_account_id': self.loss_account_id,
        }).sell_dispose()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=8500, remaining_value=34000, depreciated_value=26000, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=4000, remaining_value=28000, depreciated_value=32000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=4000, remaining_value=24000, depreciated_value=36000, state='posted'),

            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=24000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_reevaluation_increase_then_disposal(self):
        asset = self.create_asset(value=36000, periodicity="yearly", periods=3, method="linear", acquisition_date="2022-01-01", prorata_computation_type="constant_periods")
        asset.validate()
        self.loss_account_id = self.company_data['default_account_expense'].copy().id
        self.asset_counterpart_account_id = self.company_data['default_account_expense'].copy().id

        date_modify = fields.Date.to_date("2022-04-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'value_residual': asset._get_residual_value_at_date(date_modify) + 8500,
            "account_asset_counterpart_id": self.asset_counterpart_account_id,
        }).modify()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'date':  fields.Date.to_date("2022-06-30"),
            'modify_action': 'dispose',
            'loss_account_id': self.loss_account_id,
        }).sell_dispose()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=3500, remaining_value=32500, depreciated_value=3500, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=2500, remaining_value=30000, depreciated_value=6000, state='posted'),
            # disposal move
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=30000, remaining_value=0, depreciated_value=36000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            # 653.85 = 8500 * (2.5 months * 30) / (32.5 months * 30)
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=653.85, remaining_value=7846.15, depreciated_value=653.85, state='posted'),
            # disposal move
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=7846.15, remaining_value=0, depreciated_value=8500, state='draft'),
        ])

    def test_linear_reevaluation_increase_constant_periods(self):
        asset = self.create_asset(value=1200, periodicity="monthly", periods=12, method="linear", acquisition_date="2021-10-01", prorata_computation_type="constant_periods")
        asset.validate()

        date_modify = fields.Date.to_date("2022-01-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'modify_action': 'modify',
            'value_residual': asset._get_residual_value_at_date(date_modify) + 2100,
            'account_asset_counterpart_id': self.company_data['default_account_revenue'].copy().id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=100, remaining_value=1100, depreciated_value=100, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=100, remaining_value=1000, depreciated_value=200, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=100, remaining_value=900, depreciated_value=300, state='posted'),
            self._get_depreciation_move_values(date='2022-01-15', depreciation_value=48.39, remaining_value=851.61, depreciated_value=348.39, state='posted'),

            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=51.61, remaining_value=800, depreciated_value=400, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=100, remaining_value=700, depreciated_value=500, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=100, remaining_value=600, depreciated_value=600, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=100, remaining_value=500, depreciated_value=700, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=100, remaining_value=400, depreciated_value=800, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=100, remaining_value=300, depreciated_value=900, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=100, remaining_value=200, depreciated_value=1000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=100, remaining_value=100, depreciated_value=1100, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=100, remaining_value=0, depreciated_value=1200, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=127.27, remaining_value=1972.73, depreciated_value=127.27, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=246.59, remaining_value=1726.14, depreciated_value=373.86, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=246.59, remaining_value=1479.55, depreciated_value=620.45, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=246.60, remaining_value=1232.95, depreciated_value=867.05, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=246.59, remaining_value=986.36, depreciated_value=1113.64, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=246.59, remaining_value=739.77, depreciated_value=1360.23, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=246.59, remaining_value=493.18, depreciated_value=1606.82, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=246.59, remaining_value=246.59, depreciated_value=1853.41, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=246.59, remaining_value=0, depreciated_value=2100, state='draft'),
        ])

    def test_linear_reevaluation_increase_daily_computation(self):
        asset = self.create_asset(value=1200, periodicity="monthly", periods=12, method="linear", acquisition_date="2021-10-01", prorata_computation_type="daily_computation")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-01-15"),
            'modify_action': 'modify',
            'value_residual': 2945.75,
            'account_asset_counterpart_id': self.company_data['default_account_revenue'].copy().id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=101.92, remaining_value=1098.08, depreciated_value=101.92, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=98.63, remaining_value=999.45, depreciated_value=200.55, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=101.92, remaining_value=897.53, depreciated_value=302.47, state='posted'),
            self._get_depreciation_move_values(date='2022-01-15', depreciation_value=49.31, remaining_value=848.22, depreciated_value=351.78, state='posted'),

            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=52.60, remaining_value=795.62, depreciated_value=404.38, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=92.06, remaining_value=703.56, depreciated_value=496.44, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=101.92, remaining_value=601.64, depreciated_value=598.36, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=98.63, remaining_value=503.01, depreciated_value=696.99, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=101.91, remaining_value=401.10, depreciated_value=798.90, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=98.63, remaining_value=302.47, depreciated_value=897.53, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=101.92, remaining_value=200.55, depreciated_value=999.45, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=101.92, remaining_value=98.63, depreciated_value=1101.37, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=98.63, remaining_value=0, depreciated_value=1200, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=130.08, remaining_value=1967.45, depreciated_value=130.08, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=227.64, remaining_value=1739.81, depreciated_value=357.72, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=252.03, remaining_value=1487.78, depreciated_value=609.75, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=243.90, remaining_value=1243.88, depreciated_value=853.65, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=252.02, remaining_value=991.86, depreciated_value=1105.67, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=243.90, remaining_value=747.96, depreciated_value=1349.57, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=252.03, remaining_value=495.93, depreciated_value=1601.60, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=252.03, remaining_value=243.90, depreciated_value=1853.63, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=243.90, remaining_value=0, depreciated_value=2097.53, state='draft'),
        ])

    def test_linear_reevaluation_increase_amount_and_length(self):
        """ After 5 months, extend the lifetime by 3 month and the amount by 200 """
        asset = self.create_asset(value=1200, periodicity="monthly", periods=10, method="linear", acquisition_date="2022-02-01", prorata_computation_type="constant_periods")
        asset.validate()

        date_modify = fields.Date.to_date("2022-06-30")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'method_number': 10 + 3,
            'date': date_modify,
            'modify_action': 'modify',
            'value_residual': asset._get_residual_value_at_date(date_modify) + 200,
            'account_asset_counterpart_id': self.company_data['default_account_revenue'].copy().id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=120, remaining_value=1080, depreciated_value=120, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=120, remaining_value=960, depreciated_value=240, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=120, remaining_value=840, depreciated_value=360, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=120, remaining_value=720, depreciated_value=480, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=120, remaining_value=600, depreciated_value=600, state='posted'),
            # After the reeval, we divide the amount to depreciate left on the amount left
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=75, remaining_value=525, depreciated_value=675, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=75, remaining_value=450, depreciated_value=750, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=75, remaining_value=375, depreciated_value=825, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=75, remaining_value=300, depreciated_value=900, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=75, remaining_value=225, depreciated_value=975, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=75, remaining_value=150, depreciated_value=1050, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=75, remaining_value=75, depreciated_value=1125, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=75, remaining_value=0, depreciated_value=1200, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=25, remaining_value=175, depreciated_value=25, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=25, remaining_value=150, depreciated_value=50, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=25, remaining_value=125, depreciated_value=75, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=25, remaining_value=100, depreciated_value=100, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=25, remaining_value=75, depreciated_value=125, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=25, remaining_value=50, depreciated_value=150, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=25, remaining_value=25, depreciated_value=175, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=25, remaining_value=0, depreciated_value=200, state='draft'),
        ])

    def test_linear_reevaluation_decrease_amount_and_increase_length(self):
        """ After 5 months, extend the lifetime by 3 month and reduce the amount by 200 """
        asset = self.create_asset(value=1200, periodicity="monthly", periods=10, method="linear", acquisition_date="2022-02-01", prorata_computation_type="constant_periods")
        asset.validate()

        date_modify = fields.Date.to_date("2022-06-30")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'method_number': 10 + 3,
            'date': date_modify,
            'modify_action': 'modify',
            'value_residual': asset._get_residual_value_at_date(date_modify) - 200,
            'account_asset_counterpart_id': self.company_data['default_account_revenue'].copy().id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=120, remaining_value=1080, depreciated_value=120, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=120, remaining_value=960, depreciated_value=240, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=120, remaining_value=840, depreciated_value=360, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=120, remaining_value=720, depreciated_value=480, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=120, remaining_value=600, depreciated_value=600, state='posted'),
            # Decrease Move
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=200, remaining_value=400, depreciated_value=800, state='posted'),
            # After the reeval, we divide the amount to depreciate left on the amount left
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=50, remaining_value=350, depreciated_value=850, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=50, remaining_value=300, depreciated_value=900, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=50, remaining_value=250, depreciated_value=950, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=50, remaining_value=200, depreciated_value=1000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=50, remaining_value=150, depreciated_value=1050, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=50, remaining_value=100, depreciated_value=1100, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=50, remaining_value=50, depreciated_value=1150, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=50, remaining_value=0, depreciated_value=1200, state='draft'),
        ])

    def test_monthly_degressive_start_beginning_month_increase_middle_month_on_degressive_part(self):
        asset = self.degressive_asset
        asset.validate()

        date_modify = fields.Date.to_date("2022-06-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'value_residual': asset._get_residual_value_at_date(date_modify) + 8500,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=210.00, remaining_value=6990.00, depreciated_value=210.00, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=210.00, remaining_value=6780.00, depreciated_value=420.00, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=210.00, remaining_value=6570.00, depreciated_value=630.00, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=210.00, remaining_value=6360.00, depreciated_value=840.00, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=210.00, remaining_value=6150.00, depreciated_value=1050.00, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=210.00, remaining_value=5940.00, depreciated_value=1260.00, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=173.25, remaining_value=5766.75, depreciated_value=1433.25, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=173.25, remaining_value=5593.50, depreciated_value=1606.50, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=173.25, remaining_value=5420.25, depreciated_value=1779.75, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=173.25, remaining_value=5247.00, depreciated_value=1953.00, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=173.25, remaining_value=5073.75, depreciated_value=2126.25, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=173.25, remaining_value=4900.50, depreciated_value=2299.50, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=173.25, remaining_value=4727.25, depreciated_value=2472.75, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=173.25, remaining_value=4554.00, depreciated_value=2646.00, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=173.25, remaining_value=4380.75, depreciated_value=2819.25, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=173.25, remaining_value=4207.50, depreciated_value=2992.50, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=173.25, remaining_value=4034.25, depreciated_value=3165.75, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=173.25, remaining_value=3861.00, depreciated_value=3339.00, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=112.61, remaining_value=3748.39, depreciated_value=3451.61, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=112.61, remaining_value=3635.78, depreciated_value=3564.22, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=112.62, remaining_value=3523.16, depreciated_value=3676.84, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=112.61, remaining_value=3410.55, depreciated_value=3789.45, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=112.61, remaining_value=3297.94, depreciated_value=3902.06, state='posted'),
            # Increase
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=56.31, remaining_value=3241.63, depreciated_value=3958.37, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=47.27, remaining_value=3194.36, depreciated_value=4005.64, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=94.55, remaining_value=3099.81, depreciated_value=4100.19, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=94.55, remaining_value=3005.26, depreciated_value=4194.74, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=94.55, remaining_value=2910.71, depreciated_value=4289.29, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=94.54, remaining_value=2816.17, depreciated_value=4383.83, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=94.55, remaining_value=2721.62, depreciated_value=4478.38, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=94.55, remaining_value=2627.07, depreciated_value=4572.93, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=87.57, remaining_value=2539.50, depreciated_value=4660.50, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=87.57, remaining_value=2451.93, depreciated_value=4748.07, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=87.57, remaining_value=2364.36, depreciated_value=4835.64, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=87.57, remaining_value=2276.79, depreciated_value=4923.21, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=87.56, remaining_value=2189.23, depreciated_value=5010.77, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=87.57, remaining_value=2101.66, depreciated_value=5098.34, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=87.57, remaining_value=2014.09, depreciated_value=5185.91, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=87.57, remaining_value=1926.52, depreciated_value=5273.48, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=87.57, remaining_value=1838.95, depreciated_value=5361.05, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=87.57, remaining_value=1751.38, depreciated_value=5448.62, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=87.57, remaining_value=1663.81, depreciated_value=5536.19, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=87.57, remaining_value=1576.24, depreciated_value=5623.76, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=87.57, remaining_value=1488.67, depreciated_value=5711.33, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=87.57, remaining_value=1401.10, depreciated_value=5798.90, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=87.57, remaining_value=1313.53, depreciated_value=5886.47, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=87.57, remaining_value=1225.96, depreciated_value=5974.04, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=87.56, remaining_value=1138.40, depreciated_value=6061.60, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=87.57, remaining_value=1050.83, depreciated_value=6149.17, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=87.57, remaining_value=963.26, depreciated_value=6236.74, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=87.57, remaining_value=875.69, depreciated_value=6324.31, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=87.57, remaining_value=788.12, depreciated_value=6411.88, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=87.57, remaining_value=700.55, depreciated_value=6499.45, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=87.57, remaining_value=612.98, depreciated_value=6587.02, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=87.57, remaining_value=525.41, depreciated_value=6674.59, state='draft'),
            # 2025
            self._get_depreciation_move_values(date='2025-01-31', depreciation_value=87.57, remaining_value=437.84, depreciated_value=6762.16, state='draft'),
            self._get_depreciation_move_values(date='2025-02-28', depreciation_value=87.57, remaining_value=350.27, depreciated_value=6849.73, state='draft'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=87.56, remaining_value=262.71, depreciated_value=6937.29, state='draft'),
            self._get_depreciation_move_values(date='2025-04-30', depreciation_value=87.57, remaining_value=175.14, depreciated_value=7024.86, state='draft'),
            self._get_depreciation_move_values(date='2025-05-31', depreciation_value=87.57, remaining_value=87.57, depreciated_value=7112.43, state='draft'),
            self._get_depreciation_move_values(date='2025-06-30', depreciation_value=87.57, remaining_value=0.00, depreciated_value=7200.00, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=123.96, remaining_value=8376.04, depreciated_value=123.96, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=247.92, remaining_value=8128.12, depreciated_value=371.88, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=247.91, remaining_value=7880.21, depreciated_value=619.79, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=247.92, remaining_value=7632.29, depreciated_value=867.71, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=247.92, remaining_value=7384.37, depreciated_value=1115.63, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=247.91, remaining_value=7136.46, depreciated_value=1363.54, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=247.92, remaining_value=6888.54, depreciated_value=1611.46, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=229.62, remaining_value=6658.92, depreciated_value=1841.08, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=229.62, remaining_value=6429.30, depreciated_value=2070.70, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=229.61, remaining_value=6199.69, depreciated_value=2300.31, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=229.62, remaining_value=5970.07, depreciated_value=2529.93, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=229.62, remaining_value=5740.45, depreciated_value=2759.55, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=229.62, remaining_value=5510.83, depreciated_value=2989.17, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=229.62, remaining_value=5281.21, depreciated_value=3218.79, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=229.61, remaining_value=5051.60, depreciated_value=3448.40, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=229.62, remaining_value=4821.98, depreciated_value=3678.02, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=229.62, remaining_value=4592.36, depreciated_value=3907.64, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=229.62, remaining_value=4362.74, depreciated_value=4137.26, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=229.62, remaining_value=4133.12, depreciated_value=4366.88, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=229.62, remaining_value=3903.50, depreciated_value=4596.50, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=229.62, remaining_value=3673.88, depreciated_value=4826.12, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=229.61, remaining_value=3444.27, depreciated_value=5055.73, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=229.62, remaining_value=3214.65, depreciated_value=5285.35, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=229.62, remaining_value=2985.03, depreciated_value=5514.97, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=229.62, remaining_value=2755.41, depreciated_value=5744.59, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=229.61, remaining_value=2525.80, depreciated_value=5974.20, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=229.62, remaining_value=2296.18, depreciated_value=6203.82, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=229.62, remaining_value=2066.56, depreciated_value=6433.44, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=229.62, remaining_value=1836.94, depreciated_value=6663.06, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=229.62, remaining_value=1607.32, depreciated_value=6892.68, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=229.61, remaining_value=1377.71, depreciated_value=7122.29, state='draft'),
            # 2025
            self._get_depreciation_move_values(date='2025-01-31', depreciation_value=229.62, remaining_value=1148.09, depreciated_value=7351.91, state='draft'),
            self._get_depreciation_move_values(date='2025-02-28', depreciation_value=229.62, remaining_value=918.47, depreciated_value=7581.53, state='draft'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=229.62, remaining_value=688.85, depreciated_value=7811.15, state='draft'),
            self._get_depreciation_move_values(date='2025-04-30', depreciation_value=229.61, remaining_value=459.24, depreciated_value=8040.76, state='draft'),
            self._get_depreciation_move_values(date='2025-05-31', depreciation_value=229.62, remaining_value=229.62, depreciated_value=8270.38, state='draft'),
            self._get_depreciation_move_values(date='2025-06-30', depreciation_value=229.62, remaining_value=0.00, depreciated_value=8500.00, state='draft'),
        ])

    def test_monthly_degressive_start_beginning_month_increase_middle_month_on_linear_part(self):
        asset = self.degressive_asset
        asset.write({'acquisition_date': '2019-07-01'})
        asset.validate()

        date_modify = fields.Date.to_date("2022-06-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'value_residual': asset._get_residual_value_at_date(date_modify) + 8500,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2019-07-31', depreciation_value=210.00, remaining_value=6990.00, depreciated_value=210.00, state='posted'),
            self._get_depreciation_move_values(date='2019-08-31', depreciation_value=210.00, remaining_value=6780.00, depreciated_value=420.00, state='posted'),
            self._get_depreciation_move_values(date='2019-09-30', depreciation_value=210.00, remaining_value=6570.00, depreciated_value=630.00, state='posted'),
            self._get_depreciation_move_values(date='2019-10-31', depreciation_value=210.00, remaining_value=6360.00, depreciated_value=840.00, state='posted'),
            self._get_depreciation_move_values(date='2019-11-30', depreciation_value=210.00, remaining_value=6150.00, depreciated_value=1050.00, state='posted'),
            self._get_depreciation_move_values(date='2019-12-31', depreciation_value=210.00, remaining_value=5940.00, depreciated_value=1260.00, state='posted'),
            # 2020
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=173.25, remaining_value=5766.75, depreciated_value=1433.25, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=173.25, remaining_value=5593.50, depreciated_value=1606.50, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=173.25, remaining_value=5420.25, depreciated_value=1779.75, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=173.25, remaining_value=5247.00, depreciated_value=1953.00, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=173.25, remaining_value=5073.75, depreciated_value=2126.25, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=173.25, remaining_value=4900.50, depreciated_value=2299.50, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=173.25, remaining_value=4727.25, depreciated_value=2472.75, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=173.25, remaining_value=4554.00, depreciated_value=2646.00, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=173.25, remaining_value=4380.75, depreciated_value=2819.25, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=173.25, remaining_value=4207.50, depreciated_value=2992.50, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=173.25, remaining_value=4034.25, depreciated_value=3165.75, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=173.25, remaining_value=3861.00, depreciated_value=3339.00, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=112.61, remaining_value=3748.39, depreciated_value=3451.61, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=112.61, remaining_value=3635.78, depreciated_value=3564.22, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=112.62, remaining_value=3523.16, depreciated_value=3676.84, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=112.61, remaining_value=3410.55, depreciated_value=3789.45, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=112.61, remaining_value=3297.94, depreciated_value=3902.06, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=112.61, remaining_value=3185.33, depreciated_value=4014.67, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=112.62, remaining_value=3072.71, depreciated_value=4127.29, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=112.61, remaining_value=2960.10, depreciated_value=4239.90, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=112.61, remaining_value=2847.49, depreciated_value=4352.51, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=112.61, remaining_value=2734.88, depreciated_value=4465.12, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=112.62, remaining_value=2622.26, depreciated_value=4577.74, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=112.61, remaining_value=2509.65, depreciated_value=4690.35, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=83.66, remaining_value=2425.99, depreciated_value=4774.01, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=83.65, remaining_value=2342.34, depreciated_value=4857.66, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=83.65, remaining_value=2258.69, depreciated_value=4941.31, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=83.66, remaining_value=2175.03, depreciated_value=5024.97, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=83.66, remaining_value=2091.37, depreciated_value=5108.63, state='posted'),
            # Increase
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=41.82, remaining_value=2049.55, depreciated_value=5150.45, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=41.83, remaining_value=2007.72, depreciated_value=5192.28, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=83.65, remaining_value=1924.07, depreciated_value=5275.93, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=83.66, remaining_value=1840.41, depreciated_value=5359.59, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=83.65, remaining_value=1756.76, depreciated_value=5443.24, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=83.66, remaining_value=1673.10, depreciated_value=5526.90, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=83.65, remaining_value=1589.45, depreciated_value=5610.55, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=83.66, remaining_value=1505.79, depreciated_value=5694.21, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=83.66, remaining_value=1422.13, depreciated_value=5777.87, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=83.65, remaining_value=1338.48, depreciated_value=5861.52, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=83.65, remaining_value=1254.83, depreciated_value=5945.17, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=83.66, remaining_value=1171.17, depreciated_value=6028.83, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=83.65, remaining_value=1087.52, depreciated_value=6112.48, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=83.66, remaining_value=1003.86, depreciated_value=6196.14, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=83.65, remaining_value=920.21, depreciated_value=6279.79, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=83.66, remaining_value=836.55, depreciated_value=6363.45, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=83.65, remaining_value=752.90, depreciated_value=6447.10, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=83.66, remaining_value=669.24, depreciated_value=6530.76, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=83.65, remaining_value=585.59, depreciated_value=6614.41, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=83.66, remaining_value=501.93, depreciated_value=6698.07, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=83.65, remaining_value=418.28, depreciated_value=6781.72, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=83.66, remaining_value=334.62, depreciated_value=6865.38, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=83.65, remaining_value=250.97, depreciated_value=6949.03, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=83.66, remaining_value=167.31, depreciated_value=7032.69, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=83.65, remaining_value=83.66, depreciated_value=7116.34, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=83.66, remaining_value=0.00, depreciated_value=7200.00, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=173.47, remaining_value=8326.53, depreciated_value=173.47, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=346.94, remaining_value=7979.59, depreciated_value=520.41, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=346.94, remaining_value=7632.65, depreciated_value=867.35, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=346.94, remaining_value=7285.71, depreciated_value=1214.29, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=346.93, remaining_value=6938.78, depreciated_value=1561.22, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=346.94, remaining_value=6591.84, depreciated_value=1908.16, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=346.94, remaining_value=6244.90, depreciated_value=2255.10, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=346.94, remaining_value=5897.96, depreciated_value=2602.04, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=346.94, remaining_value=5551.02, depreciated_value=2948.98, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=346.94, remaining_value=5204.08, depreciated_value=3295.92, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=346.94, remaining_value=4857.14, depreciated_value=3642.86, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=346.93, remaining_value=4510.21, depreciated_value=3989.79, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=346.94, remaining_value=4163.27, depreciated_value=4336.73, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=346.94, remaining_value=3816.33, depreciated_value=4683.67, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=346.94, remaining_value=3469.39, depreciated_value=5030.61, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=346.94, remaining_value=3122.45, depreciated_value=5377.55, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=346.94, remaining_value=2775.51, depreciated_value=5724.49, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=346.94, remaining_value=2428.57, depreciated_value=6071.43, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=346.94, remaining_value=2081.63, depreciated_value=6418.37, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=346.94, remaining_value=1734.69, depreciated_value=6765.31, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=346.94, remaining_value=1387.75, depreciated_value=7112.25, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=346.94, remaining_value=1040.81, depreciated_value=7459.19, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=346.93, remaining_value=693.88, depreciated_value=7806.12, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=346.94, remaining_value=346.94, depreciated_value=8153.06, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=346.94, remaining_value=0.00, depreciated_value=8500.00, state='draft'),
        ])

    def test_monthly_degressive_start_beginning_month_decrease_middle_month(self):
        asset = self.degressive_asset
        asset.validate()

        date_modify = fields.Date.to_date("2022-06-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'value_residual': asset._get_residual_value_at_date(date_modify) - 500,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=210.00, remaining_value=6990.00, depreciated_value=210.00, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=210.00, remaining_value=6780.00, depreciated_value=420.00, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=210.00, remaining_value=6570.00, depreciated_value=630.00, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=210.00, remaining_value=6360.00, depreciated_value=840.00, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=210.00, remaining_value=6150.00, depreciated_value=1050.00, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=210.00, remaining_value=5940.00, depreciated_value=1260.00, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=173.25, remaining_value=5766.75, depreciated_value=1433.25, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=173.25, remaining_value=5593.50, depreciated_value=1606.50, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=173.25, remaining_value=5420.25, depreciated_value=1779.75, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=173.25, remaining_value=5247.00, depreciated_value=1953.00, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=173.25, remaining_value=5073.75, depreciated_value=2126.25, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=173.25, remaining_value=4900.50, depreciated_value=2299.50, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=173.25, remaining_value=4727.25, depreciated_value=2472.75, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=173.25, remaining_value=4554.00, depreciated_value=2646.00, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=173.25, remaining_value=4380.75, depreciated_value=2819.25, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=173.25, remaining_value=4207.50, depreciated_value=2992.50, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=173.25, remaining_value=4034.25, depreciated_value=3165.75, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=173.25, remaining_value=3861.00, depreciated_value=3339.00, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=112.61, remaining_value=3748.39, depreciated_value=3451.61, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=112.61, remaining_value=3635.78, depreciated_value=3564.22, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=112.62, remaining_value=3523.16, depreciated_value=3676.84, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=112.61, remaining_value=3410.55, depreciated_value=3789.45, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=112.61, remaining_value=3297.94, depreciated_value=3902.06, state='posted'),
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=56.31, remaining_value=3241.63, depreciated_value=3958.37, state='posted'),
            # Decrease
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=500.00, remaining_value=2741.63, depreciated_value=4458.37, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=39.98, remaining_value=2701.65, depreciated_value=4498.35, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=79.97, remaining_value=2621.68, depreciated_value=4578.32, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=79.96, remaining_value=2541.72, depreciated_value=4658.28, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=79.96, remaining_value=2461.76, depreciated_value=4738.24, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=79.97, remaining_value=2381.79, depreciated_value=4818.21, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=79.96, remaining_value=2301.83, depreciated_value=4898.17, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=79.97, remaining_value=2221.86, depreciated_value=4978.14, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=74.06, remaining_value=2147.80, depreciated_value=5052.20, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=74.06, remaining_value=2073.74, depreciated_value=5126.26, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=74.07, remaining_value=1999.67, depreciated_value=5200.33, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=74.06, remaining_value=1925.61, depreciated_value=5274.39, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=74.06, remaining_value=1851.55, depreciated_value=5348.45, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=74.06, remaining_value=1777.49, depreciated_value=5422.51, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=74.06, remaining_value=1703.43, depreciated_value=5496.57, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=74.07, remaining_value=1629.36, depreciated_value=5570.64, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=74.06, remaining_value=1555.30, depreciated_value=5644.70, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=74.06, remaining_value=1481.24, depreciated_value=5718.76, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=74.06, remaining_value=1407.18, depreciated_value=5792.82, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=74.06, remaining_value=1333.12, depreciated_value=5866.88, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=74.06, remaining_value=1259.06, depreciated_value=5940.94, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=74.06, remaining_value=1185.00, depreciated_value=6015.00, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=74.07, remaining_value=1110.93, depreciated_value=6089.07, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=74.06, remaining_value=1036.87, depreciated_value=6163.13, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=74.06, remaining_value=962.81, depreciated_value=6237.19, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=74.06, remaining_value=888.75, depreciated_value=6311.25, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=74.07, remaining_value=814.68, depreciated_value=6385.32, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=74.06, remaining_value=740.62, depreciated_value=6459.38, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=74.06, remaining_value=666.56, depreciated_value=6533.44, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=74.06, remaining_value=592.50, depreciated_value=6607.50, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=74.06, remaining_value=518.44, depreciated_value=6681.56, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=74.07, remaining_value=444.37, depreciated_value=6755.63, state='draft'),
            # 2025
            self._get_depreciation_move_values(date='2025-01-31', depreciation_value=74.06, remaining_value=370.31, depreciated_value=6829.69, state='draft'),
            self._get_depreciation_move_values(date='2025-02-28', depreciation_value=74.06, remaining_value=296.25, depreciated_value=6903.75, state='draft'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=74.07, remaining_value=222.18, depreciated_value=6977.82, state='draft'),
            self._get_depreciation_move_values(date='2025-04-30', depreciation_value=74.06, remaining_value=148.12, depreciated_value=7051.88, state='draft'),
            self._get_depreciation_move_values(date='2025-05-31', depreciation_value=74.06, remaining_value=74.06, depreciated_value=7125.94, state='draft'),
            self._get_depreciation_move_values(date='2025-06-30', depreciation_value=74.06, remaining_value=0.00, depreciated_value=7200.00, state='draft'),
        ])

    def test_monthly_degressive_then_linear_start_beginning_month_increase_middle_month_on_degressive_part(self):
        asset = self.degressive_then_linear_asset
        asset.validate()

        date_modify = fields.Date.to_date("2021-06-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'value_residual': asset._get_residual_value_at_date(date_modify) + 8500,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=210.00, remaining_value=6990.00, depreciated_value=210.00, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=210.00, remaining_value=6780.00, depreciated_value=420.00, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=210.00, remaining_value=6570.00, depreciated_value=630.00, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=210.00, remaining_value=6360.00, depreciated_value=840.00, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=210.00, remaining_value=6150.00, depreciated_value=1050.00, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=210.00, remaining_value=5940.00, depreciated_value=1260.00, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=173.25, remaining_value=5766.75, depreciated_value=1433.25, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=173.25, remaining_value=5593.50, depreciated_value=1606.50, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=173.25, remaining_value=5420.25, depreciated_value=1779.75, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=173.25, remaining_value=5247.00, depreciated_value=1953.00, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=173.25, remaining_value=5073.75, depreciated_value=2126.25, state='posted'),
            # Increase
            self._get_depreciation_move_values(date='2021-06-15', depreciation_value=86.63, remaining_value=4987.12, depreciated_value=2212.88, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=72.73, remaining_value=4914.39, depreciated_value=2285.61, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=145.46, remaining_value=4768.93, depreciated_value=2431.07, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=145.45, remaining_value=4623.48, depreciated_value=2576.52, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=145.46, remaining_value=4478.02, depreciated_value=2721.98, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=145.46, remaining_value=4332.56, depreciated_value=2867.44, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=145.46, remaining_value=4187.10, depreciated_value=3012.90, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=145.45, remaining_value=4041.65, depreciated_value=3158.35, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=120.00, remaining_value=3921.65, depreciated_value=3278.35, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=120.00, remaining_value=3801.65, depreciated_value=3398.35, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=120.00, remaining_value=3681.65, depreciated_value=3518.35, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=120.00, remaining_value=3561.65, depreciated_value=3638.35, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=120.00, remaining_value=3441.65, depreciated_value=3758.35, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=120.00, remaining_value=3321.65, depreciated_value=3878.35, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=120.00, remaining_value=3201.65, depreciated_value=3998.35, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=120.00, remaining_value=3081.65, depreciated_value=4118.35, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=120.00, remaining_value=2961.65, depreciated_value=4238.35, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=120.00, remaining_value=2841.65, depreciated_value=4358.35, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=120.00, remaining_value=2721.65, depreciated_value=4478.35, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=120.00, remaining_value=2601.65, depreciated_value=4598.35, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=120.00, remaining_value=2481.65, depreciated_value=4718.35, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=120.00, remaining_value=2361.65, depreciated_value=4838.35, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=120.00, remaining_value=2241.65, depreciated_value=4958.35, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=120.00, remaining_value=2121.65, depreciated_value=5078.35, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=120.00, remaining_value=2001.65, depreciated_value=5198.35, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=120.00, remaining_value=1881.65, depreciated_value=5318.35, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=120.00, remaining_value=1761.65, depreciated_value=5438.35, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=120.00, remaining_value=1641.65, depreciated_value=5558.35, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=120.00, remaining_value=1521.65, depreciated_value=5678.35, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=120.00, remaining_value=1401.65, depreciated_value=5798.35, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=120.00, remaining_value=1281.65, depreciated_value=5918.35, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=120.00, remaining_value=1161.65, depreciated_value=6038.35, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=120.00, remaining_value=1041.65, depreciated_value=6158.35, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=120.00, remaining_value=921.65, depreciated_value=6278.35, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=120.00, remaining_value=801.65, depreciated_value=6398.35, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=120.00, remaining_value=681.65, depreciated_value=6518.35, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=120.00, remaining_value=561.65, depreciated_value=6638.35, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=120.00, remaining_value=441.65, depreciated_value=6758.35, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=120.00, remaining_value=321.65, depreciated_value=6878.35, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=120.00, remaining_value=201.65, depreciated_value=6998.35, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=120.00, remaining_value=81.65, depreciated_value=7118.35, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=81.65, remaining_value=0.00, depreciated_value=7200.00, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=123.96, remaining_value=8376.04, depreciated_value=123.96, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=247.92, remaining_value=8128.12, depreciated_value=371.88, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=247.91, remaining_value=7880.21, depreciated_value=619.79, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=247.92, remaining_value=7632.29, depreciated_value=867.71, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=247.92, remaining_value=7384.37, depreciated_value=1115.63, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=247.91, remaining_value=7136.46, depreciated_value=1363.54, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=247.92, remaining_value=6888.54, depreciated_value=1611.46, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=204.52, remaining_value=6684.02, depreciated_value=1815.98, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=204.52, remaining_value=6479.50, depreciated_value=2020.50, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=204.53, remaining_value=6274.97, depreciated_value=2225.03, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=204.52, remaining_value=6070.45, depreciated_value=2429.55, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=204.52, remaining_value=5865.93, depreciated_value=2634.07, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=204.53, remaining_value=5661.40, depreciated_value=2838.60, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=204.52, remaining_value=5456.88, depreciated_value=3043.12, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=204.52, remaining_value=5252.36, depreciated_value=3247.64, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=204.53, remaining_value=5047.83, depreciated_value=3452.17, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=204.52, remaining_value=4843.31, depreciated_value=3656.69, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=204.52, remaining_value=4638.79, depreciated_value=3861.21, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=204.52, remaining_value=4434.27, depreciated_value=4065.73, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=204.53, remaining_value=4229.74, depreciated_value=4270.26, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=204.52, remaining_value=4025.22, depreciated_value=4474.78, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=204.52, remaining_value=3820.70, depreciated_value=4679.30, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=204.53, remaining_value=3616.17, depreciated_value=4883.83, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=204.52, remaining_value=3411.65, depreciated_value=5088.35, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=204.52, remaining_value=3207.13, depreciated_value=5292.87, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=204.52, remaining_value=3002.61, depreciated_value=5497.39, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=204.53, remaining_value=2798.08, depreciated_value=5701.92, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=204.52, remaining_value=2593.56, depreciated_value=5906.44, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=204.52, remaining_value=2389.04, depreciated_value=6110.96, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=204.53, remaining_value=2184.51, depreciated_value=6315.49, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=204.52, remaining_value=1979.99, depreciated_value=6520.01, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=204.52, remaining_value=1775.47, depreciated_value=6724.53, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=204.52, remaining_value=1570.95, depreciated_value=6929.05, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=204.53, remaining_value=1366.42, depreciated_value=7133.58, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=204.52, remaining_value=1161.90, depreciated_value=7338.10, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=204.52, remaining_value=957.38, depreciated_value=7542.62, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=204.53, remaining_value=752.85, depreciated_value=7747.15, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=204.52, remaining_value=548.33, depreciated_value=7951.67, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=204.52, remaining_value=343.81, depreciated_value=8156.19, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=204.53, remaining_value=139.28, depreciated_value=8360.72, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=139.28, remaining_value=0.00, depreciated_value=8500.00, state='draft'),
        ])

    def test_monthly_degressive_then_linear_start_beginning_month_increase_middle_month_on_linear_part(self):
        asset = self.degressive_then_linear_asset
        asset.validate()

        date_modify = fields.Date.to_date("2022-06-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'value_residual': asset._get_residual_value_at_date(date_modify) + 8500,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=210.00, remaining_value=6990.00, depreciated_value=210.00, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=210.00, remaining_value=6780.00, depreciated_value=420.00, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=210.00, remaining_value=6570.00, depreciated_value=630.00, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=210.00, remaining_value=6360.00, depreciated_value=840.00, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=210.00, remaining_value=6150.00, depreciated_value=1050.00, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=210.00, remaining_value=5940.00, depreciated_value=1260.00, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=173.25, remaining_value=5766.75, depreciated_value=1433.25, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=173.25, remaining_value=5593.50, depreciated_value=1606.50, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=173.25, remaining_value=5420.25, depreciated_value=1779.75, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=173.25, remaining_value=5247.00, depreciated_value=1953.00, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=173.25, remaining_value=5073.75, depreciated_value=2126.25, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=173.25, remaining_value=4900.50, depreciated_value=2299.50, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=173.25, remaining_value=4727.25, depreciated_value=2472.75, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=173.25, remaining_value=4554.00, depreciated_value=2646.00, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=173.25, remaining_value=4380.75, depreciated_value=2819.25, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=173.25, remaining_value=4207.50, depreciated_value=2992.50, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=173.25, remaining_value=4034.25, depreciated_value=3165.75, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=173.25, remaining_value=3861.00, depreciated_value=3339.00, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=120.00, remaining_value=3741.00, depreciated_value=3459.00, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=120.00, remaining_value=3621.00, depreciated_value=3579.00, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=120.00, remaining_value=3501.00, depreciated_value=3699.00, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=120.00, remaining_value=3381.00, depreciated_value=3819.00, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=120.00, remaining_value=3261.00, depreciated_value=3939.00, state='posted'),
            # Increase
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=60.00, remaining_value=3201.00, depreciated_value=3999.00, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=60.00, remaining_value=3141.00, depreciated_value=4059.00, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=120.00, remaining_value=3021.00, depreciated_value=4179.00, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=120.00, remaining_value=2901.00, depreciated_value=4299.00, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=120.00, remaining_value=2781.00, depreciated_value=4419.00, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=120.00, remaining_value=2661.00, depreciated_value=4539.00, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=120.00, remaining_value=2541.00, depreciated_value=4659.00, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=120.00, remaining_value=2421.00, depreciated_value=4779.00, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=120.00, remaining_value=2301.00, depreciated_value=4899.00, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=120.00, remaining_value=2181.00, depreciated_value=5019.00, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=120.00, remaining_value=2061.00, depreciated_value=5139.00, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=120.00, remaining_value=1941.00, depreciated_value=5259.00, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=120.00, remaining_value=1821.00, depreciated_value=5379.00, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=120.00, remaining_value=1701.00, depreciated_value=5499.00, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=120.00, remaining_value=1581.00, depreciated_value=5619.00, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=120.00, remaining_value=1461.00, depreciated_value=5739.00, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=120.00, remaining_value=1341.00, depreciated_value=5859.00, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=120.00, remaining_value=1221.00, depreciated_value=5979.00, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=120.00, remaining_value=1101.00, depreciated_value=6099.00, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=120.00, remaining_value=981.00, depreciated_value=6219.00, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=120.00, remaining_value=861.00, depreciated_value=6339.00, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=120.00, remaining_value=741.00, depreciated_value=6459.00, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=120.00, remaining_value=621.00, depreciated_value=6579.00, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=120.00, remaining_value=501.00, depreciated_value=6699.00, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=120.00, remaining_value=381.00, depreciated_value=6819.00, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=120.00, remaining_value=261.00, depreciated_value=6939.00, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=120.00, remaining_value=141.00, depreciated_value=7059.00, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=120.00, remaining_value=21.00, depreciated_value=7179.00, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=21.00, remaining_value=0.00, depreciated_value=7200.00, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=159.32, remaining_value=8340.68, depreciated_value=159.32, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=318.65, remaining_value=8022.03, depreciated_value=477.97, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=318.65, remaining_value=7703.38, depreciated_value=796.62, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=318.65, remaining_value=7384.73, depreciated_value=1115.27, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=318.65, remaining_value=7066.08, depreciated_value=1433.92, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=318.65, remaining_value=6747.43, depreciated_value=1752.57, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=318.65, remaining_value=6428.78, depreciated_value=2071.22, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=318.65, remaining_value=6110.13, depreciated_value=2389.87, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=318.65, remaining_value=5791.48, depreciated_value=2708.52, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=318.65, remaining_value=5472.83, depreciated_value=3027.17, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=318.65, remaining_value=5154.18, depreciated_value=3345.82, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=318.65, remaining_value=4835.53, depreciated_value=3664.47, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=318.65, remaining_value=4516.88, depreciated_value=3983.12, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=318.65, remaining_value=4198.23, depreciated_value=4301.77, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=318.65, remaining_value=3879.58, depreciated_value=4620.42, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=318.65, remaining_value=3560.93, depreciated_value=4939.07, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=318.65, remaining_value=3242.28, depreciated_value=5257.72, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=318.65, remaining_value=2923.63, depreciated_value=5576.37, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=318.65, remaining_value=2604.98, depreciated_value=5895.02, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=318.65, remaining_value=2286.33, depreciated_value=6213.67, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=318.65, remaining_value=1967.68, depreciated_value=6532.32, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=318.65, remaining_value=1649.03, depreciated_value=6850.97, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=318.65, remaining_value=1330.38, depreciated_value=7169.62, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=318.65, remaining_value=1011.73, depreciated_value=7488.27, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=318.65, remaining_value=693.08, depreciated_value=7806.92, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=318.65, remaining_value=374.43, depreciated_value=8125.57, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=318.65, remaining_value=55.78, depreciated_value=8444.22, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=55.78, remaining_value=0.00, depreciated_value=8500.00, state='draft'),
        ])

    def test_monthly_degressive_then_linear_start_beginning_month_decrease_middle_month(self):
        asset = self.degressive_then_linear_asset
        asset.validate()

        date_modify = fields.Date.to_date("2022-06-15")
        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  date_modify,
            'value_residual': asset._get_residual_value_at_date(date_modify) - 500,
            "account_asset_counterpart_id": self.asset_counterpart_account_id.id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=210.00, remaining_value=6990.00, depreciated_value=210.00, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=210.00, remaining_value=6780.00, depreciated_value=420.00, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=210.00, remaining_value=6570.00, depreciated_value=630.00, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=210.00, remaining_value=6360.00, depreciated_value=840.00, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=210.00, remaining_value=6150.00, depreciated_value=1050.00, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=210.00, remaining_value=5940.00, depreciated_value=1260.00, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=173.25, remaining_value=5766.75, depreciated_value=1433.25, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=173.25, remaining_value=5593.50, depreciated_value=1606.50, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=173.25, remaining_value=5420.25, depreciated_value=1779.75, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=173.25, remaining_value=5247.00, depreciated_value=1953.00, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=173.25, remaining_value=5073.75, depreciated_value=2126.25, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=173.25, remaining_value=4900.50, depreciated_value=2299.50, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=173.25, remaining_value=4727.25, depreciated_value=2472.75, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=173.25, remaining_value=4554.00, depreciated_value=2646.00, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=173.25, remaining_value=4380.75, depreciated_value=2819.25, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=173.25, remaining_value=4207.50, depreciated_value=2992.50, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=173.25, remaining_value=4034.25, depreciated_value=3165.75, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=173.25, remaining_value=3861.00, depreciated_value=3339.00, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=120.00, remaining_value=3741.00, depreciated_value=3459.00, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=120.00, remaining_value=3621.00, depreciated_value=3579.00, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=120.00, remaining_value=3501.00, depreciated_value=3699.00, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=120.00, remaining_value=3381.00, depreciated_value=3819.00, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=120.00, remaining_value=3261.00, depreciated_value=3939.00, state='posted'),
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=60.00, remaining_value=3201.00, depreciated_value=3999.00, state='posted'),
            # Decrease
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=500.00, remaining_value=2701.00, depreciated_value=4499.00, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=53.15, remaining_value=2647.85, depreciated_value=4552.15, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=106.30, remaining_value=2541.55, depreciated_value=4658.45, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=106.30, remaining_value=2435.25, depreciated_value=4764.75, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=106.30, remaining_value=2328.95, depreciated_value=4871.05, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=106.30, remaining_value=2222.65, depreciated_value=4977.35, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=106.30, remaining_value=2116.35, depreciated_value=5083.65, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=106.30, remaining_value=2010.05, depreciated_value=5189.95, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=106.30, remaining_value=1903.75, depreciated_value=5296.25, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=106.30, remaining_value=1797.45, depreciated_value=5402.55, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=106.30, remaining_value=1691.15, depreciated_value=5508.85, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=106.30, remaining_value=1584.85, depreciated_value=5615.15, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=106.30, remaining_value=1478.55, depreciated_value=5721.45, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=106.30, remaining_value=1372.25, depreciated_value=5827.75, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=106.30, remaining_value=1265.95, depreciated_value=5934.05, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=106.30, remaining_value=1159.65, depreciated_value=6040.35, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=106.30, remaining_value=1053.35, depreciated_value=6146.65, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=106.30, remaining_value=947.05, depreciated_value=6252.95, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=106.30, remaining_value=840.75, depreciated_value=6359.25, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=106.30, remaining_value=734.45, depreciated_value=6465.55, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=106.30, remaining_value=628.15, depreciated_value=6571.85, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=106.30, remaining_value=521.85, depreciated_value=6678.15, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=106.30, remaining_value=415.55, depreciated_value=6784.45, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=106.30, remaining_value=309.25, depreciated_value=6890.75, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=106.30, remaining_value=202.95, depreciated_value=6997.05, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=106.30, remaining_value=96.65, depreciated_value=7103.35, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=96.65, remaining_value=0.00, depreciated_value=7200.00, state='draft'),
        ])

    def test_linear_modify_0_value_residual(self):
        """Set the value residual to 0"""
        asset = self.create_asset(value=10000, periodicity="monthly", periods=10, method="linear", acquisition_date="2022-02-01", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'method_number': 4,
            'date': fields.Date.to_date("2022-06-24"),
            'modify_action': 'modify',
            'value_residual': 0,
            'account_asset_counterpart_id': self.company_data['default_account_revenue'].copy().id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=1000, remaining_value=9000, depreciated_value=1000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=1000, remaining_value=8000, depreciated_value=2000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=1000, remaining_value=7000, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=6000, depreciated_value=4000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-24', depreciation_value=800, remaining_value=5200, depreciated_value=4800, state='posted'),

            self._get_depreciation_move_values(date='2022-06-24', depreciation_value=5200, remaining_value=0, depreciated_value=10000, state='posted'),
        ])

    def test_asset_modify_value_residual_after_reversal(self):
        """ Tests the special case of residual amounts on a board with a reverse entry.
            It keeps its focus on the computed residual amount in the modify asset wizard as for now,
            the recomputation after a modify on a board with reverse entries is broken. This should be corrected in a later task."""

        asset = self.create_asset(value=1000, periodicity="yearly", periods=5, method="linear", acquisition_date="2020-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=200, remaining_value=800, depreciated_value=200, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=200, remaining_value=600, depreciated_value=400, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=200, remaining_value=400, depreciated_value=600, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=200, remaining_value=200, depreciated_value=800, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=200, remaining_value=0, depreciated_value=1000, state='draft'),
        ])

        move_to_reverse = asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id))[0]
        self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=move_to_reverse.ids)\
            .create({
                'journal_id': move_to_reverse.journal_id.id
            }).reverse_moves()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=200, remaining_value=800, depreciated_value=200, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=200, remaining_value=600, depreciated_value=400, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=-200, remaining_value=800, depreciated_value=200, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=400, remaining_value=400, depreciated_value=600, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=200, remaining_value=200, depreciated_value=800, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=200, remaining_value=0, depreciated_value=1000, state='draft'),
        ])

        asset_modify = self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date': fields.Date.to_date("2022-06-30"),
            'modify_action': 'modify',
        })

        # We want to show the actual remaining value of the asset.
        self.assertEqual(asset_modify.value_residual, 500, "The computation of the value_residual in asset.modify shouldn't care about the reversal.")

    def test_asset_gain_or_loss_account(self):
        asset = self.create_asset(value=1000, periodicity="yearly", periods=5, method="linear", acquisition_date="2020-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': '2022-06-30',
            'invoice_line_ids': [(0, 0, {
                'name': 'Asset sold',
                'tax_ids': [],
                'price_unit': 500,
            })],
        })
        invoice.action_post()

        asset_modify = self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date': fields.Date.to_date('2022-06-10'),
            'modify_action': 'sell',
            'invoice_ids': invoice.ids,
            'invoice_line_ids': invoice.invoice_line_ids.ids
        })
        # The remaining value of the asset on 2022-06-30 is 500: if the asset is sold before that date, it will result in a loss (and a gain if sold after)
        self.assertEqual(asset_modify.gain_or_loss, 'loss')

        asset_modify.date = fields.Date.from_string('2022-07-15')
        self.assertEqual(asset_modify.gain_or_loss, 'gain')

        asset_modify.date = fields.Date.from_string('2022-06-30')
        self.assertEqual(asset_modify.gain_or_loss, 'no')

    def test_asset_disposal_on_hashed_journal(self):
        asset = self.create_asset(
            value=3000,
            periodicity='monthly',
            periods=3,
            method='linear',
            acquisition_date='2022-05-01',
            prorata_computation_type='constant_periods',
        )
        asset.journal_id.restrict_mode_hash_table = True
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'date':  fields.Date.to_date('2022-05-15'),
            'modify_action': 'dispose',
            'loss_account_id': self.company_data['default_account_expense'].copy().id,
        }).sell_dispose()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-05-15', depreciation_value=483.87, remaining_value=2516.13, depreciated_value=483.87, state='posted'),
            self._get_depreciation_move_values(date='2022-05-15', depreciation_value=2516.13, remaining_value=0, depreciated_value=3000, state='draft'),
            # At this point the asset is disposed, which means its 'remaining_value' is 0.
            # But the next 2 depreciation moves could not be removed due to the hash on the journal.
            # This results in a negative 'remaining_value' and a 'depreciated_value' that exceeds the asset's initial value.
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=-1000, depreciated_value=4000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=-2000, depreciated_value=5000, state='posted'),
            # The next 2 depreciation moves are reverting the previous 2,
            # bringing the 'remaining_value' back to 0 on the last one, as it should be.
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=-1000, remaining_value=-1000, depreciated_value=4000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=-1000, remaining_value=0, depreciated_value=3000, state='posted'),
        ])

    def test_asset_disposal_with_audit_trail(self):
        asset = self.create_asset(
            value=3000,
            periodicity='monthly',
            periods=3,
            method='linear',
            acquisition_date='2022-05-01',
            prorata_computation_type='constant_periods',
        )
        asset.validate()

        with patch.object(self.env.registry['account.move'], '_is_protected_by_audit_trail', lambda move: True):
            self.env['asset.modify'].create({
                'asset_id': asset.id,
                'date':  fields.Date.to_date('2022-06-15'),
                'modify_action': 'dispose',
                'loss_account_id': self.company_data['default_account_expense'].copy().id,
            }).sell_dispose()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=2000, depreciated_value=1000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=500, remaining_value=1500, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=1500, remaining_value=0, depreciated_value=3000, state='draft'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=0, depreciated_value=3000, state='cancel'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=0, depreciated_value=3000, state='cancel'),
        ])

    def test_disposal_of_fully_depreciated_asset(self):
        asset = self.create_asset(value=10000, periodicity="yearly", periods=2, method="degressive", acquisition_date="2020-01-01", prorata_computation_type="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'date':  fields.Date.to_date("2022-01-01"),
            'modify_action': 'dispose',
            'loss_account_id': self.company_data['default_account_expense'].copy().id,
        }).sell_dispose()

    def test_asset_disposal_in_middle_of_fiscal_year(self):
        self.company_data['company'].fiscalyear_last_month = "3"

        asset = self.create_asset(value=10000, periodicity="monthly", periods=12, method="degressive", acquisition_date="2022-01-01", prorata_computation_type="daily_computation")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'date':  fields.Date.to_date("2022-02-24"),
            'modify_action': 'dispose',
            'loss_account_id': self.company_data['default_account_expense'].copy().id,
        }).sell_dispose()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=849.32, remaining_value=9150.68, depreciated_value=849.32, state='posted'),
            self._get_depreciation_move_values(date='2022-02-24', depreciation_value=657.53, remaining_value=8493.15, depreciated_value=1506.85, state='posted'),
            self._get_depreciation_move_values(date='2022-02-24', depreciation_value=8493.15, remaining_value=0, depreciated_value=10000, state='draft'),
        ])
