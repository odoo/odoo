# -*- coding: utf-8 -*-


from freezegun import freeze_time
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import fields


@freeze_time('2022-07-01')
@tagged('post_install', '-at_install')
class TestAccountAssetNew(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref)
        cls.car = cls.create_asset(value=60000, periodicity="yearly", periods=5, method="linear", salvage_value=0)

    @classmethod
    def create_asset(cls, value, periodicity, periods, degressive_factor=None, import_depreciation=0, **kwargs):
        if degressive_factor is not None:
            kwargs["method_progress_factor"] = degressive_factor
        return cls.env['account.asset'].create({
            'name': 'nice asset',
            'account_asset_id': cls.company_data['default_account_assets'].id,
            'account_depreciation_id': cls.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': cls.company_data['default_account_expense'].id,
            'journal_id': cls.company_data['default_journal_misc'].id,
            'acquisition_date': "2020-02-01",
            'prorata_computation_type': 'none',
            'original_value': value,
            'salvage_value': 0,
            'method_number': periods,
            'method_period': '12' if periodicity == "yearly" else '1',
            'method': "linear",
            'already_depreciated_amount_import': import_depreciation,
            **kwargs,
        })

    @classmethod
    def _get_depreciation_move_values(cls, date, depreciation_value, remaining_value, depreciated_value, state):
        return {
            'date': fields.Date.from_string(date),
            'depreciation_value': depreciation_value,
            'asset_remaining_value': remaining_value,
            'asset_depreciated_value': depreciated_value,
            'state': state,
        }

    def test_linear_5_years_no_prorata_asset(self):
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=12000, remaining_value=48000, depreciated_value=12000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=24000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_5_years_no_prorata_with_imported_amount_asset(self):
        self.car.write({'already_depreciated_amount_import': 1000})
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=11000, remaining_value=48000, depreciated_value=11000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=23000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=35000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=47000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_linear_5_years_no_prorata_with_salvage_value_asset(self):
        self.car.write({'salvage_value': 1000})
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36400)
        self.assertEqual(self.car.value_residual, 35400)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=11800, remaining_value=47200, depreciated_value=11800, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=11800, remaining_value=35400, depreciated_value=23600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=11800, remaining_value=23600, depreciated_value=35400, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=11800, remaining_value=11800, depreciated_value=47200, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=11800, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_linear_5_years_constant_periods_asset(self):
        self.car.write({
            'prorata_computation_type': 'constant_periods',
            'prorata_date': '2020-07-01',
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 42000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=6000, remaining_value=54000, depreciated_value=6000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=42000, depreciated_value=18000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=30000, depreciated_value=30000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=18000, depreciated_value=42000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=6000, depreciated_value=54000, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=6000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_5_years_daily_computation_asset(self):
        self.car.write({
            'prorata_computation_type': 'daily_computation',
            'prorata_date': '2020-07-01',
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 41960.57)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=6046, remaining_value=53954, depreciated_value=6046, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=11993.43, remaining_value=41960.57, depreciated_value=18039.43, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=11993.43, remaining_value=29967.14, depreciated_value=30032.86, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=11993.43, remaining_value=17973.71, depreciated_value=42026.29, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12026.28, remaining_value=5947.43, depreciated_value=54052.57, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=5947.43, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_degressive_5_years_no_prorata_asset(self):
        self.car.write({
            'method': 'degressive',
            'method_progress_factor': 0.3,
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 29400)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=18000, remaining_value=42000, depreciated_value=18000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12600, remaining_value=29400, depreciated_value=30600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=9800, remaining_value=19600, depreciated_value=40400, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=9800, remaining_value=9800, depreciated_value=50200, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=9800, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_degressive_5_years_no_prorata_with_imported_amount_asset(self):
        self.car.write({
            'method': 'degressive',
            'method_progress_factor': 0.3,
            'already_depreciated_amount_import': 1000,
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 29400)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=17000, remaining_value=42000, depreciated_value=17000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12600, remaining_value=29400, depreciated_value=29600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=9800, remaining_value=19600, depreciated_value=39400, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=9800, remaining_value=9800, depreciated_value=49200, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=9800, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_degressive_5_years_no_prorata_with_salvage_value_asset(self):
        self.car.write({
            'method': 'degressive',
            'method_progress_factor': 0.3,
            'salvage_value': 1000,
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 29910)
        self.assertEqual(self.car.value_residual, 28910)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=17700, remaining_value=41300, depreciated_value=17700, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12390, remaining_value=28910, depreciated_value=30090, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=9636.67, remaining_value=19273.33, depreciated_value=39726.67, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=9636.67, remaining_value=9636.66, depreciated_value=49363.34, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=9636.66, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_degressive_then_linear_5_years_no_prorata_asset(self):
        asset = self.create_asset(value=60000, periodicity="yearly", periods=5, method="degressive_then_linear", degressive_factor=0.3)
        asset.validate()
        self.assertEqual(asset.state, 'open')
        self.assertEqual(asset.book_value, 29400)
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=18000, remaining_value=42000, depreciated_value=18000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12600, remaining_value=29400, depreciated_value=30600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=17400, depreciated_value=42600, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=5400, depreciated_value=54600, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=5400, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_degressive_then_linear_5_years_no_prorata_negative_asset(self):
        asset = self.create_asset(value=-60000, periodicity="yearly", periods=5, method="degressive_then_linear", degressive_factor=0.3)
        asset.validate()
        self.assertEqual(asset.state, 'open')
        self.assertEqual(asset.book_value, -29400)
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=-18000, remaining_value=-42000, depreciated_value=-18000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=-12600, remaining_value=-29400, depreciated_value=-30600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=-12000, remaining_value=-17400, depreciated_value=-42600, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=-12000, remaining_value=-5400, depreciated_value=-54600, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=-5400, remaining_value=0, depreciated_value=-60000, state='draft'),
        ])

    def test_degressive_than_linear_5_years_no_prorata_with_imported_amount_asset(self):
        asset = self.create_asset(value=60000, periodicity="yearly", periods=5, method="degressive_then_linear", degressive_factor=0.3, import_depreciation=1000)
        asset.validate()
        self.assertEqual(asset.state, 'open')
        self.assertEqual(asset.book_value, 29400)
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=18000-1000, remaining_value=42000, depreciated_value=17000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12600, remaining_value=29400, depreciated_value=29600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=17400, depreciated_value=41600, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=5400, depreciated_value=53600, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=5400, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_degressive_than_linear_5_years_no_prorata_with_imported_amount_negative_asset(self):
        asset = self.create_asset(value=-60000, periodicity="yearly", periods=5, method="degressive_then_linear", degressive_factor=0.3, import_depreciation=-1000)
        asset.validate()
        self.assertEqual(asset.state, 'open')
        self.assertEqual(asset.book_value, -29400)
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=-18000+1000, remaining_value=-42000, depreciated_value=-17000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=-12600, remaining_value=-29400, depreciated_value=-29600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=-12000, remaining_value=-17400, depreciated_value=-41600, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=-12000, remaining_value=-5400, depreciated_value=-53600, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=-5400, remaining_value=0, depreciated_value=-59000, state='draft'),
        ])

    def test_degressive_than_linear_5_years_no_prorata_with_salvage_value_asset(self):
        asset = self.create_asset(value=60000, periodicity="yearly", periods=5, salvage_value=1000, method="degressive_then_linear", degressive_factor=0.3)
        asset.validate()
        self.assertEqual(asset.state, 'open')
        self.assertEqual(asset.value_residual, 28910)
        self.assertEqual(asset.book_value, 28910 + 1000)
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=17700, remaining_value=41300, depreciated_value=17700, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12390, remaining_value=28910, depreciated_value=30090, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=11800, remaining_value=17110, depreciated_value=41890, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=11800, remaining_value=5310, depreciated_value=53690, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=5310, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_degressive_then_linear_36_month_constant_period_asset(self):
        """
        The depreciation amount is computed that way: Compute a degressive amount for each year and split it by month linearly.
        The depreciation value could vary by one currency unit to absorb small differences that are created over time.
        """
        asset = self.create_asset(value=10000, periodicity="monthly", periods=36, method="degressive_then_linear", degressive_factor=0.4)
        asset.validate()
        self.assertEqual(asset.state, 'open')
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=333.33, remaining_value=9666.67, depreciated_value=333.33, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=333.34, remaining_value=9333.33, depreciated_value=666.67, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=333.33, remaining_value=9000.00, depreciated_value=1000.00, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=333.33, remaining_value=8666.67, depreciated_value=1333.33, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=333.34, remaining_value=8333.33, depreciated_value=1666.67, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=333.33, remaining_value=8000.00, depreciated_value=2000.00, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=333.33, remaining_value=7666.67, depreciated_value=2333.33, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=333.34, remaining_value=7333.33, depreciated_value=2666.67, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=333.33, remaining_value=7000.00, depreciated_value=3000.00, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=333.33, remaining_value=6666.67, depreciated_value=3333.33, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=333.34, remaining_value=6333.33, depreciated_value=3666.67, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=333.33, remaining_value=6000.00, depreciated_value=4000.00, state='posted'),
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=277.78, remaining_value=5722.22, depreciated_value=4277.78, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=277.78, remaining_value=5444.44, depreciated_value=4555.56, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=277.78, remaining_value=5166.66, depreciated_value=4833.34, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=277.77, remaining_value=4888.89, depreciated_value=5111.11, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=277.78, remaining_value=4611.11, depreciated_value=5388.89, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=277.78, remaining_value=4333.33, depreciated_value=5666.67, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=277.78, remaining_value=4055.55, depreciated_value=5944.45, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=277.78, remaining_value=3777.77, depreciated_value=6222.23, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=277.77, remaining_value=3500.00, depreciated_value=6500.00, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=277.78, remaining_value=3222.22, depreciated_value=6777.78, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=277.78, remaining_value=2944.44, depreciated_value=7055.56, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=277.78, remaining_value=2666.66, depreciated_value=7333.34, state='posted'),
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=277.77, remaining_value=2388.89, depreciated_value=7611.11, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=277.78, remaining_value=2111.11, depreciated_value=7888.89, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=277.78, remaining_value=1833.33, depreciated_value=8166.67, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=277.78, remaining_value=1555.55, depreciated_value=8444.45, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=277.78, remaining_value=1277.77, depreciated_value=8722.23, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=277.77, remaining_value=1000.00, depreciated_value=9000.00, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=277.78, remaining_value=722.22, depreciated_value=9277.78, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=277.78, remaining_value=444.44, depreciated_value=9555.56, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=277.78, remaining_value=166.66, depreciated_value=9833.34, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=166.66, remaining_value=0.00, depreciated_value=10000.00, state='draft'),
        ])


    @freeze_time('2022-06-15')
    def test_asset_degressive_then_linear_prorata_start_middle_of_year(self):
        """ Check the computation of an asset with degressive-linear method,
            start at middle of the year
        """
        asset = self.create_asset(
            value=10000,
            periodicity="yearly",
            periods=5,
            method="degressive_then_linear",
            degressive_factor=0.3,
            acquisition_date="2021-07-01",
            prorata_computation_type="constant_periods",
        )
        asset.validate()
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1500.00, remaining_value=8500.00, depreciated_value=1500.0000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=2550.00, remaining_value=5950.00, depreciated_value=4050.000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=2000.00, remaining_value=3950.00, depreciated_value=6050.000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=2000.00, remaining_value=1950.00, depreciated_value=8050.000, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=1950.00, remaining_value=0.00, depreciated_value=10000.000, state='draft'),
        ])

    def test_asset_degressive_then_linear_prorata_start_middle_of_year_monthly(self):
        """ Check the computation of an asset with degressive-linear method,
            start at middle of the year, monthly depreciations
        """
        asset = self.create_asset(
            value=10000,
            periodicity="monthly",
            periods=36,
            method="degressive_then_linear",
            degressive_factor=0.6,
            acquisition_date="2021-07-01",
            prorata_computation_type="constant_periods",
        )
        asset.validate()
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=500.00, remaining_value=9500.00, depreciated_value=500.00, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=500.00, remaining_value=9000.00, depreciated_value=1000.00, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=500.00, remaining_value=8500.00, depreciated_value=1500.00, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=500.00, remaining_value=8000.00, depreciated_value=2000.00, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=500.00, remaining_value=7500.00, depreciated_value=2500.00, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=500.00, remaining_value=7000.00, depreciated_value=3000.00, state='posted'),

            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=350.00, remaining_value=6650.00, depreciated_value=3350.00, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=350.00, remaining_value=6300.00, depreciated_value=3700.00, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=350.00, remaining_value=5950.00, depreciated_value=4050.00, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=350.00, remaining_value=5600.00, depreciated_value=4400.00, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=350.00, remaining_value=5250.00, depreciated_value=4750.00, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=350.00, remaining_value=4900.00, depreciated_value=5100.00, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=350.00, remaining_value=4550.00, depreciated_value=5450.00, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=350.00, remaining_value=4200.00, depreciated_value=5800.00, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=350.00, remaining_value=3850.00, depreciated_value=6150.00, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=350.00, remaining_value=3500.00, depreciated_value=6500.00, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=350.00, remaining_value=3150.00, depreciated_value=6850.00, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=350.00, remaining_value=2800.00, depreciated_value=7200.00, state='draft'),

            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=277.78, remaining_value=2522.22, depreciated_value=7477.78, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=277.78, remaining_value=2244.44, depreciated_value=7755.56, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=277.77, remaining_value=1966.67, depreciated_value=8033.33, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=277.78, remaining_value=1688.89, depreciated_value=8311.11, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=277.78, remaining_value=1411.11, depreciated_value=8588.89, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=277.78, remaining_value=1133.33, depreciated_value=8866.67, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=277.77, remaining_value=855.56, depreciated_value=9144.44, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=277.78, remaining_value=577.78, depreciated_value=9422.22, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=277.78, remaining_value=300.00, depreciated_value=9700.00, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=277.78, remaining_value=22.22, depreciated_value=9977.78, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=22.22, remaining_value=0.00, depreciated_value=10000.00, state='draft'),
        ])

    def test_linear_60_months_no_prorata_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 30000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=1000, remaining_value=59000, depreciated_value=1000, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=1000, remaining_value=58000, depreciated_value=2000, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1000, remaining_value=57000, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1000, remaining_value=56000, depreciated_value=4000, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1000, remaining_value=54000, depreciated_value=6000, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1000, remaining_value=53000, depreciated_value=7000, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1000, remaining_value=52000, depreciated_value=8000, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1000, remaining_value=51000, depreciated_value=9000, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1000, remaining_value=49000, depreciated_value=11000, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1000, remaining_value=48000, depreciated_value=12000, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1000, remaining_value=47000, depreciated_value=13000, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1000, remaining_value=46000, depreciated_value=14000, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1000, remaining_value=44000, depreciated_value=16000, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1000, remaining_value=43000, depreciated_value=17000, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1000, remaining_value=42000, depreciated_value=18000, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1000, remaining_value=41000, depreciated_value=19000, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1000, remaining_value=40000, depreciated_value=20000, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1000, remaining_value=39000, depreciated_value=21000, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1000, remaining_value=38000, depreciated_value=22000, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1000, remaining_value=37000, depreciated_value=23000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1000, remaining_value=36000, depreciated_value=24000, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=1000, remaining_value=35000, depreciated_value=25000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=1000, remaining_value=34000, depreciated_value=26000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=1000, remaining_value=33000, depreciated_value=27000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=1000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=31000, depreciated_value=29000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=30000, depreciated_value=30000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=29000, depreciated_value=31000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=28000, depreciated_value=32000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=27000, depreciated_value=33000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=26000, depreciated_value=34000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=25000, depreciated_value=35000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=24000, depreciated_value=36000, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=1000, remaining_value=23000, depreciated_value=37000, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=1000, remaining_value=22000, depreciated_value=38000, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=1000, remaining_value=21000, depreciated_value=39000, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=1000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=1000, remaining_value=19000, depreciated_value=41000, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=1000, remaining_value=18000, depreciated_value=42000, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=1000, remaining_value=17000, depreciated_value=43000, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=1000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=1000, remaining_value=15000, depreciated_value=45000, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=1000, remaining_value=14000, depreciated_value=46000, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=1000, remaining_value=13000, depreciated_value=47000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=1000, remaining_value=12000, depreciated_value=48000, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1000, remaining_value=11000, depreciated_value=49000, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=1000, remaining_value=10000, depreciated_value=50000, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1000, remaining_value=9000, depreciated_value=51000, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=1000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1000, remaining_value=7000, depreciated_value=53000, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=1000, remaining_value=6000, depreciated_value=54000, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=55000, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=57000, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=58000, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=59000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_60_months_no_prorata_with_imported_amount_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'already_depreciated_amount_import': 1500,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 30000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=500.0, remaining_value=58000.0, depreciated_value=500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1000.0, remaining_value=57000.0, depreciated_value=1500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1000.0, remaining_value=56000.0, depreciated_value=2500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1000.0, remaining_value=55000.0, depreciated_value=3500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1000.0, remaining_value=54000.0, depreciated_value=4500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1000.0, remaining_value=53000.0, depreciated_value=5500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1000.0, remaining_value=52000.0, depreciated_value=6500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1000.0, remaining_value=51000.0, depreciated_value=7500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1000.0, remaining_value=50000.0, depreciated_value=8500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1000.0, remaining_value=49000.0, depreciated_value=9500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1000.0, remaining_value=48000.0, depreciated_value=10500.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1000.0, remaining_value=47000.0, depreciated_value=11500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1000.0, remaining_value=46000.0, depreciated_value=12500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1000.0, remaining_value=45000.0, depreciated_value=13500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1000.0, remaining_value=44000.0, depreciated_value=14500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1000.0, remaining_value=43000.0, depreciated_value=15500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1000.0, remaining_value=42000.0, depreciated_value=16500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1000.0, remaining_value=41000.0, depreciated_value=17500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1000.0, remaining_value=40000.0, depreciated_value=18500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1000.0, remaining_value=39000.0, depreciated_value=19500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1000.0, remaining_value=38000.0, depreciated_value=20500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1000.0, remaining_value=37000.0, depreciated_value=21500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1000.0, remaining_value=36000.0, depreciated_value=22500.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=1000.0, remaining_value=35000.0, depreciated_value=23500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=1000.0, remaining_value=34000.0, depreciated_value=24500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=1000.0, remaining_value=33000.0, depreciated_value=25500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=1000.0, remaining_value=32000.0, depreciated_value=26500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000.0, remaining_value=31000.0, depreciated_value=27500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000.0, remaining_value=30000.0, depreciated_value=28500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000.0, remaining_value=29000.0, depreciated_value=29500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000.0, remaining_value=28000.0, depreciated_value=30500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000.0, remaining_value=27000.0, depreciated_value=31500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000.0, remaining_value=26000.0, depreciated_value=32500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000.0, remaining_value=25000.0, depreciated_value=33500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000.0, remaining_value=24000.0, depreciated_value=34500.0, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=1000.0, remaining_value=23000.0, depreciated_value=35500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=1000.0, remaining_value=22000.0, depreciated_value=36500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=1000.0, remaining_value=21000.0, depreciated_value=37500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=1000.0, remaining_value=20000.0, depreciated_value=38500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=1000.0, remaining_value=19000.0, depreciated_value=39500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=1000.0, remaining_value=18000.0, depreciated_value=40500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=1000.0, remaining_value=17000.0, depreciated_value=41500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=1000.0, remaining_value=16000.0, depreciated_value=42500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=1000.0, remaining_value=15000.0, depreciated_value=43500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=1000.0, remaining_value=14000.0, depreciated_value=44500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=1000.0, remaining_value=13000.0, depreciated_value=45500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=1000.0, remaining_value=12000.0, depreciated_value=46500.0, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1000.0, remaining_value=11000.0, depreciated_value=47500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=1000.0, remaining_value=10000.0, depreciated_value=48500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1000.0, remaining_value=9000.0, depreciated_value=49500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=1000.0, remaining_value=8000.0, depreciated_value=50500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1000.0, remaining_value=7000.0, depreciated_value=51500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=1000.0, remaining_value=6000.0, depreciated_value=52500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1000.0, remaining_value=5000.0, depreciated_value=53500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1000.0, remaining_value=4000.0, depreciated_value=54500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=1000.0, remaining_value=3000.0, depreciated_value=55500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1000.0, remaining_value=2000.0, depreciated_value=56500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=1000.0, remaining_value=1000.0, depreciated_value=57500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1000.0, remaining_value=0.0, depreciated_value=58500.0, state='draft'),
        ])

    def test_linear_60_months_no_prorata_with_salvage_value_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'method_progress_factor': 0.3,
            'salvage_value': 2000,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 31000)
        self.assertEqual(self.car.value_residual, 29000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=966.67, remaining_value=57033.33, depreciated_value=966.67, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=966.66, remaining_value=56066.67, depreciated_value=1933.33, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=966.67, remaining_value=55100.0, depreciated_value=2900.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=966.67, remaining_value=54133.33, depreciated_value=3866.67, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=966.66, remaining_value=53166.67, depreciated_value=4833.33, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=966.67, remaining_value=52200.0, depreciated_value=5800.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=966.67, remaining_value=51233.33, depreciated_value=6766.67, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=966.66, remaining_value=50266.67, depreciated_value=7733.33, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=966.67, remaining_value=49300.0, depreciated_value=8700.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=966.67, remaining_value=48333.33, depreciated_value=9666.67, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=966.66, remaining_value=47366.67, depreciated_value=10633.33, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=966.67, remaining_value=46400.0, depreciated_value=11600.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=966.67, remaining_value=45433.33, depreciated_value=12566.67, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=966.66, remaining_value=44466.67, depreciated_value=13533.33, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=966.67, remaining_value=43500.0, depreciated_value=14500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=966.67, remaining_value=42533.33, depreciated_value=15466.67, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=966.66, remaining_value=41566.67, depreciated_value=16433.33, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=966.67, remaining_value=40600.0, depreciated_value=17400.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=966.67, remaining_value=39633.33, depreciated_value=18366.67, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=966.66, remaining_value=38666.67, depreciated_value=19333.33, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=966.67, remaining_value=37700.0, depreciated_value=20300.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=966.67, remaining_value=36733.33, depreciated_value=21266.67, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=966.66, remaining_value=35766.67, depreciated_value=22233.33, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=966.67, remaining_value=34800.0, depreciated_value=23200.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=966.67, remaining_value=33833.33, depreciated_value=24166.67, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=966.66, remaining_value=32866.67, depreciated_value=25133.33, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=966.67, remaining_value=31900.0, depreciated_value=26100.0, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=966.67, remaining_value=30933.33, depreciated_value=27066.67, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=966.66, remaining_value=29966.67, depreciated_value=28033.33, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=966.67, remaining_value=29000.0, depreciated_value=29000.0, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=966.67, remaining_value=28033.33, depreciated_value=29966.67, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=966.66, remaining_value=27066.67, depreciated_value=30933.33, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=966.67, remaining_value=26100.0, depreciated_value=31900.0, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=966.67, remaining_value=25133.33, depreciated_value=32866.67, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=966.66, remaining_value=24166.67, depreciated_value=33833.33, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=966.67, remaining_value=23200.0, depreciated_value=34800.0, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=966.67, remaining_value=22233.33, depreciated_value=35766.67, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=966.66, remaining_value=21266.67, depreciated_value=36733.33, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=966.67, remaining_value=20300.0, depreciated_value=37700.0, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=966.67, remaining_value=19333.33, depreciated_value=38666.67, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=966.66, remaining_value=18366.67, depreciated_value=39633.33, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=966.67, remaining_value=17400.0, depreciated_value=40600.0, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=966.67, remaining_value=16433.33, depreciated_value=41566.67, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=966.66, remaining_value=15466.67, depreciated_value=42533.33, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=966.67, remaining_value=14500.0, depreciated_value=43500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=966.67, remaining_value=13533.33, depreciated_value=44466.67, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=966.66, remaining_value=12566.67, depreciated_value=45433.33, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=966.67, remaining_value=11600.0, depreciated_value=46400.0, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=966.67, remaining_value=10633.33, depreciated_value=47366.67, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=966.66, remaining_value=9666.67, depreciated_value=48333.33, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=966.67, remaining_value=8700.0, depreciated_value=49300.0, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=966.67, remaining_value=7733.33, depreciated_value=50266.67, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=966.66, remaining_value=6766.67, depreciated_value=51233.33, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=966.67, remaining_value=5800.0, depreciated_value=52200.0, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=966.67, remaining_value=4833.33, depreciated_value=53166.67, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=966.66, remaining_value=3866.67, depreciated_value=54133.33, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=966.67, remaining_value=2900.0, depreciated_value=55100.0, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=966.67, remaining_value=1933.33, depreciated_value=56066.67, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=966.66, remaining_value=966.67, depreciated_value=57033.33, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=966.67, remaining_value=0.0, depreciated_value=58000.0, state='draft'),
        ])

    def test_linear_60_months_constant_periods_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'prorata_computation_type': 'constant_periods',
            'prorata_date': '2020-07-01',
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1000, remaining_value=59000, depreciated_value=1000, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1000, remaining_value=58000, depreciated_value=2000, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1000, remaining_value=57000, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1000, remaining_value=56000, depreciated_value=4000, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1000, remaining_value=54000, depreciated_value=6000, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1000, remaining_value=53000, depreciated_value=7000, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1000, remaining_value=52000, depreciated_value=8000, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1000, remaining_value=51000, depreciated_value=9000, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1000, remaining_value=49000, depreciated_value=11000, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1000, remaining_value=48000, depreciated_value=12000, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1000, remaining_value=47000, depreciated_value=13000, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1000, remaining_value=46000, depreciated_value=14000, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1000, remaining_value=44000, depreciated_value=16000, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1000, remaining_value=43000, depreciated_value=17000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1000, remaining_value=42000, depreciated_value=18000, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=1000, remaining_value=41000, depreciated_value=19000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=1000, remaining_value=40000, depreciated_value=20000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=1000, remaining_value=39000, depreciated_value=21000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=1000, remaining_value=38000, depreciated_value=22000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=37000, depreciated_value=23000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=36000, depreciated_value=24000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=35000, depreciated_value=25000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=34000, depreciated_value=26000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=33000, depreciated_value=27000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=32000, depreciated_value=28000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=31000, depreciated_value=29000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=30000, depreciated_value=30000, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=1000, remaining_value=29000, depreciated_value=31000, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=1000, remaining_value=28000, depreciated_value=32000, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=1000, remaining_value=27000, depreciated_value=33000, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=1000, remaining_value=26000, depreciated_value=34000, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=1000, remaining_value=25000, depreciated_value=35000, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=1000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=1000, remaining_value=23000, depreciated_value=37000, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=1000, remaining_value=22000, depreciated_value=38000, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=1000, remaining_value=21000, depreciated_value=39000, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=1000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=1000, remaining_value=19000, depreciated_value=41000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=1000, remaining_value=18000, depreciated_value=42000, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1000, remaining_value=17000, depreciated_value=43000, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=1000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1000, remaining_value=15000, depreciated_value=45000, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=1000, remaining_value=14000, depreciated_value=46000, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1000, remaining_value=13000, depreciated_value=47000, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=1000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1000, remaining_value=11000, depreciated_value=49000, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1000, remaining_value=10000, depreciated_value=50000, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=1000, remaining_value=9000, depreciated_value=51000, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=1000, remaining_value=7000, depreciated_value=53000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1000, remaining_value=6000, depreciated_value=54000, state='draft'),
            # 2025
            self._get_depreciation_move_values(date='2025-01-31', depreciation_value=1000, remaining_value=5000, depreciated_value=55000, state='draft'),
            self._get_depreciation_move_values(date='2025-02-28', depreciation_value=1000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=1000, remaining_value=3000, depreciated_value=57000, state='draft'),
            self._get_depreciation_move_values(date='2025-04-30', depreciation_value=1000, remaining_value=2000, depreciated_value=58000, state='draft'),
            self._get_depreciation_move_values(date='2025-05-31', depreciation_value=1000, remaining_value=1000, depreciated_value=59000, state='draft'),
            self._get_depreciation_move_values(date='2025-06-30', depreciation_value=1000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_60_months_daily_computation_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'prorata_computation_type': 'daily_computation',
            'prorata_date': '2020-07-01',
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36013.14)

        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1018.62, remaining_value=58981.38, depreciated_value=1018.62, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1018.62, remaining_value=57962.76, depreciated_value=2037.24, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=985.76, remaining_value=56977.0, depreciated_value=3023.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1018.62, remaining_value=55958.38, depreciated_value=4041.62, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=985.76, remaining_value=54972.62, depreciated_value=5027.38, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1018.62, remaining_value=53954.0, depreciated_value=6046.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1018.62, remaining_value=52935.38, depreciated_value=7064.62, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=920.05, remaining_value=52015.33, depreciated_value=7984.67, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1018.62, remaining_value=50996.71, depreciated_value=9003.29, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=985.76, remaining_value=50010.95, depreciated_value=9989.05, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1018.62, remaining_value=48992.33, depreciated_value=11007.67, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=985.76, remaining_value=48006.57, depreciated_value=11993.43, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1018.62, remaining_value=46987.95, depreciated_value=13012.05, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1018.62, remaining_value=45969.33, depreciated_value=14030.67, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=985.76, remaining_value=44983.57, depreciated_value=15016.43, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1018.62, remaining_value=43964.95, depreciated_value=16035.05, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=985.76, remaining_value=42979.19, depreciated_value=17020.81, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1018.62, remaining_value=41960.57, depreciated_value=18039.43, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=1018.62, remaining_value=40941.95, depreciated_value=19058.05, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=920.04, remaining_value=40021.91, depreciated_value=19978.09, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=1018.62, remaining_value=39003.29, depreciated_value=20996.71, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=985.77, remaining_value=38017.52, depreciated_value=21982.48, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1018.62, remaining_value=36998.9, depreciated_value=23001.10, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=985.76, remaining_value=36013.14, depreciated_value=23986.86, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1018.62, remaining_value=34994.52, depreciated_value=25005.48, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1018.62, remaining_value=33975.9, depreciated_value=26024.10, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=985.76, remaining_value=32990.14, depreciated_value=27009.86, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1018.62, remaining_value=31971.52, depreciated_value=28028.48, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=985.76, remaining_value=30985.76, depreciated_value=29014.24, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1018.62, remaining_value=29967.14, depreciated_value=30032.86, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=1018.62, remaining_value=28948.52, depreciated_value=31051.48, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=920.04, remaining_value=28028.48, depreciated_value=31971.52, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=1018.62, remaining_value=27009.86, depreciated_value=32990.14, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=985.76, remaining_value=26024.10, depreciated_value=33975.9, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=1018.62, remaining_value=25005.48, depreciated_value=34994.52, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=985.76, remaining_value=24019.72, depreciated_value=35980.28, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=1018.62, remaining_value=23001.10, depreciated_value=36998.9, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=1018.62, remaining_value=21982.48, depreciated_value=38017.52, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=985.77, remaining_value=20996.71, depreciated_value=39003.29, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=1018.62, remaining_value=19978.09, depreciated_value=40021.91, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=985.76, remaining_value=18992.33, depreciated_value=41007.67, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=1018.62, remaining_value=17973.71, depreciated_value=42026.29, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1018.62, remaining_value=16955.09, depreciated_value=43044.91, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=952.9, remaining_value=16002.19, depreciated_value=43997.81, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1018.62, remaining_value=14983.57, depreciated_value=45016.43, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=985.76, remaining_value=13997.81, depreciated_value=46002.19, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1018.62, remaining_value=12979.19, depreciated_value=47020.81, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=985.76, remaining_value=11993.43, depreciated_value=48006.57, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1018.62, remaining_value=10974.81, depreciated_value=49025.19, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1018.62, remaining_value=9956.19, depreciated_value=50043.81, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=985.76, remaining_value=8970.43, depreciated_value=51029.57, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1018.62, remaining_value=7951.81, depreciated_value=52048.19, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=985.76, remaining_value=6966.05, depreciated_value=53033.95, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1018.62, remaining_value=5947.43, depreciated_value=54052.57, state='draft'),
            # 2025
            self._get_depreciation_move_values(date='2025-01-31', depreciation_value=1018.62, remaining_value=4928.81, depreciated_value=55071.19, state='draft'),
            self._get_depreciation_move_values(date='2025-02-28', depreciation_value=920.05, remaining_value=4008.76, depreciated_value=55991.24, state='draft'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=1018.62, remaining_value=2990.14, depreciated_value=57009.86, state='draft'),
            self._get_depreciation_move_values(date='2025-04-30', depreciation_value=985.76, remaining_value=2004.38, depreciated_value=57995.62, state='draft'),
            self._get_depreciation_move_values(date='2025-05-31', depreciation_value=1018.62, remaining_value=985.76, depreciated_value=59014.24, state='draft'),
            self._get_depreciation_move_values(date='2025-06-30', depreciation_value=985.76, remaining_value=0.0, depreciated_value=60000.0, state='draft'),
        ])

    def test_degressive_60_months_no_prorata_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'method': 'degressive',
            'method_progress_factor': 0.3,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 24500)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=1500.0, remaining_value=58500.0, depreciated_value=1500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=1500.0, remaining_value=57000.0, depreciated_value=3000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1500.0, remaining_value=55500.0, depreciated_value=4500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1500.0, remaining_value=54000.0, depreciated_value=6000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1500.0, remaining_value=52500.0, depreciated_value=7500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1500.0, remaining_value=51000.0, depreciated_value=9000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1500.0, remaining_value=49500.0, depreciated_value=10500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1500.0, remaining_value=48000.0, depreciated_value=12000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1500.0, remaining_value=46500.0, depreciated_value=13500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1500.0, remaining_value=45000.0, depreciated_value=15000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1500.0, remaining_value=43500.0, depreciated_value=16500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1500.0, remaining_value=42000.0, depreciated_value=18000.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1050.0, remaining_value=40950.0, depreciated_value=19050.0, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1050.0, remaining_value=39900.0, depreciated_value=20100.0, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1050.0, remaining_value=38850.0, depreciated_value=21150.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1050.0, remaining_value=37800.0, depreciated_value=22200.0, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1050.0, remaining_value=36750.0, depreciated_value=23250.0, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1050.0, remaining_value=35700.0, depreciated_value=24300.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1050.0, remaining_value=34650.0, depreciated_value=25350.0, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1050.0, remaining_value=33600.0, depreciated_value=26400.0, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1050.0, remaining_value=32550.0, depreciated_value=27450.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1050.0, remaining_value=31500.0, depreciated_value=28500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1050.0, remaining_value=30450.0, depreciated_value=29550.0, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1050.0, remaining_value=29400.0, depreciated_value=30600.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=816.67, remaining_value=28583.33, depreciated_value=31416.67, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=816.66, remaining_value=27766.67, depreciated_value=32233.33, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=816.67, remaining_value=26950.0, depreciated_value=33050.0, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=816.67, remaining_value=26133.33, depreciated_value=33866.67, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=816.66, remaining_value=25316.67, depreciated_value=34683.33, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=816.67, remaining_value=24500.0, depreciated_value=35500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=816.67, remaining_value=23683.33, depreciated_value=36316.67, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=816.66, remaining_value=22866.67, depreciated_value=37133.33, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=816.67, remaining_value=22050.0, depreciated_value=37950.0, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=816.67, remaining_value=21233.33, depreciated_value=38766.67, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=816.66, remaining_value=20416.67, depreciated_value=39583.33, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=816.67, remaining_value=19600.0, depreciated_value=40400.0, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=816.67, remaining_value=18783.33, depreciated_value=41216.67, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=816.66, remaining_value=17966.67, depreciated_value=42033.33, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=816.67, remaining_value=17150.0, depreciated_value=42850.0, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=816.67, remaining_value=16333.33, depreciated_value=43666.67, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=816.66, remaining_value=15516.67, depreciated_value=44483.33, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=816.67, remaining_value=14700.0, depreciated_value=45300.0, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=816.67, remaining_value=13883.33, depreciated_value=46116.67, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=816.66, remaining_value=13066.67, depreciated_value=46933.33, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=816.67, remaining_value=12250.0, depreciated_value=47750.0, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=816.67, remaining_value=11433.33, depreciated_value=48566.67, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=816.66, remaining_value=10616.67, depreciated_value=49383.33, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=816.67, remaining_value=9800.0, depreciated_value=50200.0, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=816.67, remaining_value=8983.33, depreciated_value=51016.67, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=816.66, remaining_value=8166.67, depreciated_value=51833.33, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=816.67, remaining_value=7350.0, depreciated_value=52650.0, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=816.67, remaining_value=6533.33, depreciated_value=53466.67, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=816.66, remaining_value=5716.67, depreciated_value=54283.33, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=816.67, remaining_value=4900.0, depreciated_value=55100.0, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=816.67, remaining_value=4083.33, depreciated_value=55916.67, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=816.66, remaining_value=3266.67, depreciated_value=56733.33, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=816.67, remaining_value=2450.0, depreciated_value=57550.0, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=816.67, remaining_value=1633.33, depreciated_value=58366.67, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=816.66, remaining_value=816.67, depreciated_value=59183.33, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=816.67, remaining_value=0.0, depreciated_value=60000.0, state='draft'),
        ])

    def test_degressive_60_months_from_middle_year(self):
        asset = self.create_asset(
            value=100000,
            periodicity='monthly',
            periods=60,
            method='degressive',
            method_progress_factor=0.35,
            acquisition_date='2022-07-01',
            prorata_computation_type='constant_periods'
        )
        asset.compute_depreciation_board()
        self.assertEqual(asset.state, 'draft')
        self.assertEqual(asset.book_value, 100000)
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=2916.67, remaining_value=97083.33, depreciated_value=2916.67, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=2916.66, remaining_value=94166.67, depreciated_value=5833.33, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=2916.67, remaining_value=91250.00, depreciated_value=8750.00, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=2916.67, remaining_value=88333.33, depreciated_value=11666.67, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=2916.66, remaining_value=85416.67, depreciated_value=14583.33, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=2916.67, remaining_value=82500.00, depreciated_value=17500.00, state='draft'),

            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=2406.25, remaining_value=80093.75, depreciated_value=19906.25, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=2406.25, remaining_value=77687.50, depreciated_value=22312.50, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=2406.25, remaining_value=75281.25, depreciated_value=24718.75, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=2406.25, remaining_value=72875.00, depreciated_value=27125.00, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=2406.25, remaining_value=70468.75, depreciated_value=29531.25, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=2406.25, remaining_value=68062.50, depreciated_value=31937.50, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=2406.25, remaining_value=65656.25, depreciated_value=34343.75, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=2406.25, remaining_value=63250.00, depreciated_value=36750.00, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=2406.25, remaining_value=60843.75, depreciated_value=39156.25, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=2406.25, remaining_value=58437.50, depreciated_value=41562.50, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=2406.25, remaining_value=56031.25, depreciated_value=43968.75, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=2406.25, remaining_value=53625.00, depreciated_value=46375.00, state='draft'),

            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1564.06, remaining_value=52060.94, depreciated_value=47939.06, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=1564.07, remaining_value=50496.87, depreciated_value=49503.13, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1564.06, remaining_value=48932.81, depreciated_value=51067.19, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=1564.06, remaining_value=47368.75, depreciated_value=52631.25, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1564.06, remaining_value=45804.69, depreciated_value=54195.31, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=1564.07, remaining_value=44240.62, depreciated_value=55759.38, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1564.06, remaining_value=42676.56, depreciated_value=57323.44, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1564.06, remaining_value=41112.50, depreciated_value=58887.50, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=1564.06, remaining_value=39548.44, depreciated_value=60451.56, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1564.07, remaining_value=37984.37, depreciated_value=62015.63, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=1564.06, remaining_value=36420.31, depreciated_value=63579.69, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1564.06, remaining_value=34856.25, depreciated_value=65143.75, state='draft'),

            self._get_depreciation_move_values(date='2025-01-31', depreciation_value=1161.88, remaining_value=33694.37, depreciated_value=66305.63, state='draft'),
            self._get_depreciation_move_values(date='2025-02-28', depreciation_value=1161.87, remaining_value=32532.50, depreciated_value=67467.50, state='draft'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=1161.88, remaining_value=31370.62, depreciated_value=68629.38, state='draft'),
            self._get_depreciation_move_values(date='2025-04-30', depreciation_value=1161.87, remaining_value=30208.75, depreciated_value=69791.25, state='draft'),
            self._get_depreciation_move_values(date='2025-05-31', depreciation_value=1161.88, remaining_value=29046.87, depreciated_value=70953.13, state='draft'),
            self._get_depreciation_move_values(date='2025-06-30', depreciation_value=1161.87, remaining_value=27885.00, depreciated_value=72115.00, state='draft'),
            self._get_depreciation_move_values(date='2025-07-31', depreciation_value=1161.88, remaining_value=26723.12, depreciated_value=73276.88, state='draft'),
            self._get_depreciation_move_values(date='2025-08-31', depreciation_value=1161.87, remaining_value=25561.25, depreciated_value=74438.75, state='draft'),
            self._get_depreciation_move_values(date='2025-09-30', depreciation_value=1161.88, remaining_value=24399.37, depreciated_value=75600.63, state='draft'),
            self._get_depreciation_move_values(date='2025-10-31', depreciation_value=1161.87, remaining_value=23237.50, depreciated_value=76762.50, state='draft'),
            self._get_depreciation_move_values(date='2025-11-30', depreciation_value=1161.88, remaining_value=22075.62, depreciated_value=77924.38, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=1161.87, remaining_value=20913.75, depreciated_value=79086.25, state='draft'),

            self._get_depreciation_move_values(date='2026-01-31', depreciation_value=1161.88, remaining_value=19751.87, depreciated_value=80248.13, state='draft'),
            self._get_depreciation_move_values(date='2026-02-28', depreciation_value=1161.87, remaining_value=18590.00, depreciated_value=81410.00, state='draft'),
            self._get_depreciation_move_values(date='2026-03-31', depreciation_value=1161.88, remaining_value=17428.12, depreciated_value=82571.88, state='draft'),
            self._get_depreciation_move_values(date='2026-04-30', depreciation_value=1161.87, remaining_value=16266.25, depreciated_value=83733.75, state='draft'),
            self._get_depreciation_move_values(date='2026-05-31', depreciation_value=1161.88, remaining_value=15104.37, depreciated_value=84895.63, state='draft'),
            self._get_depreciation_move_values(date='2026-06-30', depreciation_value=1161.87, remaining_value=13942.50, depreciated_value=86057.50, state='draft'),
            self._get_depreciation_move_values(date='2026-07-31', depreciation_value=1161.88, remaining_value=12780.62, depreciated_value=87219.38, state='draft'),
            self._get_depreciation_move_values(date='2026-08-31', depreciation_value=1161.87, remaining_value=11618.75, depreciated_value=88381.25, state='draft'),
            self._get_depreciation_move_values(date='2026-09-30', depreciation_value=1161.88, remaining_value=10456.87, depreciated_value=89543.13, state='draft'),
            self._get_depreciation_move_values(date='2026-10-31', depreciation_value=1161.87, remaining_value=9295.00, depreciated_value=90705.00, state='draft'),
            self._get_depreciation_move_values(date='2026-11-30', depreciation_value=1161.88, remaining_value=8133.12, depreciated_value=91866.88, state='draft'),
            self._get_depreciation_move_values(date='2026-12-31', depreciation_value=1161.87, remaining_value=6971.25, depreciated_value=93028.75, state='draft'),

            self._get_depreciation_move_values(date='2027-01-31', depreciation_value=1161.88, remaining_value=5809.37, depreciated_value=94190.63, state='draft'),
            self._get_depreciation_move_values(date='2027-02-28', depreciation_value=1161.87, remaining_value=4647.50, depreciated_value=95352.50, state='draft'),
            self._get_depreciation_move_values(date='2027-03-31', depreciation_value=1161.88, remaining_value=3485.62, depreciated_value=96514.38, state='draft'),
            self._get_depreciation_move_values(date='2027-04-30', depreciation_value=1161.87, remaining_value=2323.75, depreciated_value=97676.25, state='draft'),
            self._get_depreciation_move_values(date='2027-05-31', depreciation_value=1161.88, remaining_value=1161.87, depreciated_value=98838.13, state='draft'),
            self._get_depreciation_move_values(date='2027-06-30', depreciation_value=1161.87, remaining_value=0.00, depreciated_value=100000.00, state='draft'),
        ])

    def test_degressive_60_months_from_middle_sync_with_fiscalyear(self):
        company = self.env.company
        company.fiscalyear_last_day = 30
        company.fiscalyear_last_month = '6'
        asset = self.create_asset(
            value=100000,
            periodicity='monthly',
            periods=60,
            method='degressive',
            method_progress_factor=0.35,
            acquisition_date='2022-07-01',
            prorata_computation_type='constant_periods'
        )
        asset.compute_depreciation_board()
        self.assertEqual(asset.state, 'draft')
        self.assertEqual(asset.book_value, 100000)
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=2916.67, remaining_value=97083.33, depreciated_value=2916.67, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=2916.66, remaining_value=94166.67, depreciated_value=5833.33, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=2916.67, remaining_value=91250.00, depreciated_value=8750.00, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=2916.67, remaining_value=88333.33, depreciated_value=11666.67, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=2916.66, remaining_value=85416.67, depreciated_value=14583.33, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=2916.67, remaining_value=82500.00, depreciated_value=17500.00, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=2916.67, remaining_value=79583.33, depreciated_value=20416.67, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=2916.66, remaining_value=76666.67, depreciated_value=23333.33, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=2916.67, remaining_value=73750.00, depreciated_value=26250.00, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=2916.67, remaining_value=70833.33, depreciated_value=29166.67, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=2916.66, remaining_value=67916.67, depreciated_value=32083.33, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=2916.67, remaining_value=65000.00, depreciated_value=35000.00, state='draft'),

            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=1895.83, remaining_value=63104.17, depreciated_value=36895.83, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=1895.84, remaining_value=61208.33, depreciated_value=38791.67, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=1895.83, remaining_value=59312.50, depreciated_value=40687.50, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=1895.83, remaining_value=57416.67, depreciated_value=42583.33, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=1895.84, remaining_value=55520.83, depreciated_value=44479.17, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=1895.83, remaining_value=53625.00, depreciated_value=46375.00, state='draft'),
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1895.83, remaining_value=51729.17, depreciated_value=48270.83, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=1895.84, remaining_value=49833.33, depreciated_value=50166.67, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1895.83, remaining_value=47937.50, depreciated_value=52062.50, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=1895.83, remaining_value=46041.67, depreciated_value=53958.33, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1895.84, remaining_value=44145.83, depreciated_value=55854.17, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=1895.83, remaining_value=42250.00, depreciated_value=57750.00, state='draft'),

            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1232.29, remaining_value=41017.71, depreciated_value=58982.29, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1232.29, remaining_value=39785.42, depreciated_value=60214.58, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=1232.29, remaining_value=38553.13, depreciated_value=61446.87, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1232.30, remaining_value=37320.83, depreciated_value=62679.17, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=1232.29, remaining_value=36088.54, depreciated_value=63911.46, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1232.29, remaining_value=34856.25, depreciated_value=65143.75, state='draft'),
            self._get_depreciation_move_values(date='2025-01-31', depreciation_value=1232.29, remaining_value=33623.96, depreciated_value=66376.04, state='draft'),
            self._get_depreciation_move_values(date='2025-02-28', depreciation_value=1232.29, remaining_value=32391.67, depreciated_value=67608.33, state='draft'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=1232.29, remaining_value=31159.38, depreciated_value=68840.62, state='draft'),
            self._get_depreciation_move_values(date='2025-04-30', depreciation_value=1232.30, remaining_value=29927.08, depreciated_value=70072.92, state='draft'),
            self._get_depreciation_move_values(date='2025-05-31', depreciation_value=1232.29, remaining_value=28694.79, depreciated_value=71305.21, state='draft'),
            self._get_depreciation_move_values(date='2025-06-30', depreciation_value=1232.29, remaining_value=27462.50, depreciated_value=72537.50, state='draft'),

            self._get_depreciation_move_values(date='2025-07-31', depreciation_value=1144.27, remaining_value=26318.23, depreciated_value=73681.77, state='draft'),
            self._get_depreciation_move_values(date='2025-08-31', depreciation_value=1144.27, remaining_value=25173.96, depreciated_value=74826.04, state='draft'),
            self._get_depreciation_move_values(date='2025-09-30', depreciation_value=1144.27, remaining_value=24029.69, depreciated_value=75970.31, state='draft'),
            self._get_depreciation_move_values(date='2025-10-31', depreciation_value=1144.27, remaining_value=22885.42, depreciated_value=77114.58, state='draft'),
            self._get_depreciation_move_values(date='2025-11-30', depreciation_value=1144.27, remaining_value=21741.15, depreciated_value=78258.85, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=1144.27, remaining_value=20596.88, depreciated_value=79403.12, state='draft'),
            self._get_depreciation_move_values(date='2026-01-31', depreciation_value=1144.28, remaining_value=19452.60, depreciated_value=80547.40, state='draft'),
            self._get_depreciation_move_values(date='2026-02-28', depreciation_value=1144.27, remaining_value=18308.33, depreciated_value=81691.67, state='draft'),
            self._get_depreciation_move_values(date='2026-03-31', depreciation_value=1144.27, remaining_value=17164.06, depreciated_value=82835.94, state='draft'),
            self._get_depreciation_move_values(date='2026-04-30', depreciation_value=1144.27, remaining_value=16019.79, depreciated_value=83980.21, state='draft'),
            self._get_depreciation_move_values(date='2026-05-31', depreciation_value=1144.27, remaining_value=14875.52, depreciated_value=85124.48, state='draft'),
            self._get_depreciation_move_values(date='2026-06-30', depreciation_value=1144.27, remaining_value=13731.25, depreciated_value=86268.75, state='draft'),

            self._get_depreciation_move_values(date='2026-07-31', depreciation_value=1144.27, remaining_value=12586.98, depreciated_value=87413.02, state='draft'),
            self._get_depreciation_move_values(date='2026-08-31', depreciation_value=1144.27, remaining_value=11442.71, depreciated_value=88557.29, state='draft'),
            self._get_depreciation_move_values(date='2026-09-30', depreciation_value=1144.27, remaining_value=10298.44, depreciated_value=89701.56, state='draft'),
            self._get_depreciation_move_values(date='2026-10-31', depreciation_value=1144.27, remaining_value=9154.17, depreciated_value=90845.83, state='draft'),
            self._get_depreciation_move_values(date='2026-11-30', depreciation_value=1144.27, remaining_value=8009.90, depreciated_value=91990.10, state='draft'),
            self._get_depreciation_move_values(date='2026-12-31', depreciation_value=1144.27, remaining_value=6865.63, depreciated_value=93134.37, state='draft'),
            self._get_depreciation_move_values(date='2027-01-31', depreciation_value=1144.28, remaining_value=5721.35, depreciated_value=94278.65, state='draft'),
            self._get_depreciation_move_values(date='2027-02-28', depreciation_value=1144.27, remaining_value=4577.08, depreciated_value=95422.92, state='draft'),
            self._get_depreciation_move_values(date='2027-03-31', depreciation_value=1144.27, remaining_value=3432.81, depreciated_value=96567.19, state='draft'),
            self._get_depreciation_move_values(date='2027-04-30', depreciation_value=1144.27, remaining_value=2288.54, depreciated_value=97711.46, state='draft'),
            self._get_depreciation_move_values(date='2027-05-31', depreciation_value=1144.27, remaining_value=1144.27, depreciated_value=98855.73, state='draft'),
            self._get_depreciation_move_values(date='2027-06-30', depreciation_value=1144.27, remaining_value=0.00, depreciated_value=100000.00, state='draft'),
        ])

    def test_degressive_60_months_no_prorata_with_imported_amount_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'method': 'degressive',
            'method_progress_factor': 0.3,
            'already_depreciated_amount_import': 2000,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 24500)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=1000.0, remaining_value=57000.0, depreciated_value=1000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1500.0, remaining_value=55500.0, depreciated_value=2500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1500.0, remaining_value=54000.0, depreciated_value=4000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1500.0, remaining_value=52500.0, depreciated_value=5500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1500.0, remaining_value=51000.0, depreciated_value=7000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1500.0, remaining_value=49500.0, depreciated_value=8500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1500.0, remaining_value=48000.0, depreciated_value=10000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1500.0, remaining_value=46500.0, depreciated_value=11500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1500.0, remaining_value=45000.0, depreciated_value=13000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1500.0, remaining_value=43500.0, depreciated_value=14500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1500.0, remaining_value=42000.0, depreciated_value=16000.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1050.0, remaining_value=40950.0, depreciated_value=17050.0, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1050.0, remaining_value=39900.0, depreciated_value=18100.0, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1050.0, remaining_value=38850.0, depreciated_value=19150.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1050.0, remaining_value=37800.0, depreciated_value=20200.0, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1050.0, remaining_value=36750.0, depreciated_value=21250.0, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1050.0, remaining_value=35700.0, depreciated_value=22300.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1050.0, remaining_value=34650.0, depreciated_value=23350.0, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1050.0, remaining_value=33600.0, depreciated_value=24400.0, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1050.0, remaining_value=32550.0, depreciated_value=25450.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1050.0, remaining_value=31500.0, depreciated_value=26500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1050.0, remaining_value=30450.0, depreciated_value=27550.0, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1050.0, remaining_value=29400.0, depreciated_value=28600.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=816.67, remaining_value=28583.33, depreciated_value=29416.67, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=816.66, remaining_value=27766.67, depreciated_value=30233.33, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=816.67, remaining_value=26950.0, depreciated_value=31050.0, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=816.67, remaining_value=26133.33, depreciated_value=31866.67, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=816.66, remaining_value=25316.67, depreciated_value=32683.33, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=816.67, remaining_value=24500.0, depreciated_value=33500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=816.67, remaining_value=23683.33, depreciated_value=34316.67, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=816.66, remaining_value=22866.67, depreciated_value=35133.33, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=816.67, remaining_value=22050.0, depreciated_value=35950.0, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=816.67, remaining_value=21233.33, depreciated_value=36766.67, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=816.66, remaining_value=20416.67, depreciated_value=37583.33, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=816.67, remaining_value=19600.0, depreciated_value=38400.0, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=816.67, remaining_value=18783.33, depreciated_value=39216.67, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=816.66, remaining_value=17966.67, depreciated_value=40033.33, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=816.67, remaining_value=17150.0, depreciated_value=40850.0, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=816.67, remaining_value=16333.33, depreciated_value=41666.67, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=816.66, remaining_value=15516.67, depreciated_value=42483.33, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=816.67, remaining_value=14700.0, depreciated_value=43300.0, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=816.67, remaining_value=13883.33, depreciated_value=44116.67, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=816.66, remaining_value=13066.67, depreciated_value=44933.33, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=816.67, remaining_value=12250.0, depreciated_value=45750.0, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=816.67, remaining_value=11433.33, depreciated_value=46566.67, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=816.66, remaining_value=10616.67, depreciated_value=47383.33, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=816.67, remaining_value=9800.0, depreciated_value=48200.0, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=816.67, remaining_value=8983.33, depreciated_value=49016.67, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=816.66, remaining_value=8166.67, depreciated_value=49833.33, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=816.67, remaining_value=7350.0, depreciated_value=50650.0, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=816.67, remaining_value=6533.33, depreciated_value=51466.67, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=816.66, remaining_value=5716.67, depreciated_value=52283.33, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=816.67, remaining_value=4900.0, depreciated_value=53100.0, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=816.67, remaining_value=4083.33, depreciated_value=53916.67, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=816.66, remaining_value=3266.67, depreciated_value=54733.33, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=816.67, remaining_value=2450.0, depreciated_value=55550.0, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=816.67, remaining_value=1633.33, depreciated_value=56366.67, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=816.66, remaining_value=816.67, depreciated_value=57183.33, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=816.67, remaining_value=0.0, depreciated_value=58000.0, state='draft'),
        ])

    def test_degressive_60_months_no_prorata_with_salvage_value_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'method': 'degressive',
            'method_progress_factor': 0.3,
            'salvage_value': 2000,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 25683.33)
        self.assertEqual(self.car.value_residual, 23683.33)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=1450.0, remaining_value=56550.0, depreciated_value=1450.0, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=1450.0, remaining_value=55100.0, depreciated_value=2900.0, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1450.0, remaining_value=53650.0, depreciated_value=4350.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1450.0, remaining_value=52200.0, depreciated_value=5800.0, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1450.0, remaining_value=50750.0, depreciated_value=7250.0, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1450.0, remaining_value=49300.0, depreciated_value=8700.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1450.0, remaining_value=47850.0, depreciated_value=10150.0, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1450.0, remaining_value=46400.0, depreciated_value=11600.0, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1450.0, remaining_value=44950.0, depreciated_value=13050.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1450.0, remaining_value=43500.0, depreciated_value=14500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1450.0, remaining_value=42050.0, depreciated_value=15950.0, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1450.0, remaining_value=40600.0, depreciated_value=17400.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1015.0, remaining_value=39585.0, depreciated_value=18415.0, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1015.0, remaining_value=38570.0, depreciated_value=19430.0, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1015.0, remaining_value=37555.0, depreciated_value=20445.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1015.0, remaining_value=36540.0, depreciated_value=21460.0, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1015.0, remaining_value=35525.0, depreciated_value=22475.0, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1015.0, remaining_value=34510.0, depreciated_value=23490.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1015.0, remaining_value=33495.0, depreciated_value=24505.0, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1015.0, remaining_value=32480.0, depreciated_value=25520.0, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1015.0, remaining_value=31465.0, depreciated_value=26535.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1015.0, remaining_value=30450.0, depreciated_value=27550.0, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1015.0, remaining_value=29435.0, depreciated_value=28565.0, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1015.0, remaining_value=28420.0, depreciated_value=29580.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=789.44, remaining_value=27630.56, depreciated_value=30369.44, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=789.45, remaining_value=26841.11, depreciated_value=31158.89, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=789.44, remaining_value=26051.67, depreciated_value=31948.33, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=789.45, remaining_value=25262.22, depreciated_value=32737.78, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=789.44, remaining_value=24472.78, depreciated_value=33527.22, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=789.45, remaining_value=23683.33, depreciated_value=34316.67, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=789.44, remaining_value=22893.89, depreciated_value=35106.11, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=789.45, remaining_value=22104.44, depreciated_value=35895.56, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=789.44, remaining_value=21315.0, depreciated_value=36685.0, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=789.44, remaining_value=20525.56, depreciated_value=37474.44, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=789.45, remaining_value=19736.11, depreciated_value=38263.89, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=789.44, remaining_value=18946.67, depreciated_value=39053.33, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=789.44, remaining_value=18157.23, depreciated_value=39842.77, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=789.45, remaining_value=17367.78, depreciated_value=40632.22, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=789.44, remaining_value=16578.34, depreciated_value=41421.66, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=789.45, remaining_value=15788.89, depreciated_value=42211.11, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=789.44, remaining_value=14999.45, depreciated_value=43000.55, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=789.45, remaining_value=14210.0, depreciated_value=43790.0, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=789.44, remaining_value=13420.56, depreciated_value=44579.44, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=789.45, remaining_value=12631.11, depreciated_value=45368.89, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=789.44, remaining_value=11841.67, depreciated_value=46158.33, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=789.45, remaining_value=11052.22, depreciated_value=46947.78, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=789.44, remaining_value=10262.78, depreciated_value=47737.22, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=789.44, remaining_value=9473.34, depreciated_value=48526.66, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=789.44, remaining_value=8683.9, depreciated_value=49316.1, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=789.45, remaining_value=7894.45, depreciated_value=50105.55, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=789.45, remaining_value=7105.0, depreciated_value=50895.0, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=789.44, remaining_value=6315.56, depreciated_value=51684.44, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=789.44, remaining_value=5526.12, depreciated_value=52473.88, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=789.45, remaining_value=4736.67, depreciated_value=53263.33, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=789.44, remaining_value=3947.23, depreciated_value=54052.77, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=789.45, remaining_value=3157.78, depreciated_value=54842.22, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=789.45, remaining_value=2368.33, depreciated_value=55631.67, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=789.44, remaining_value=1578.89, depreciated_value=56421.11, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=789.45, remaining_value=789.44, depreciated_value=57210.56, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=789.44, remaining_value=0.0, depreciated_value=58000.0, state='draft'),
        ])

    def test_degressive_5_years_from_beggining_of_year(self):
        asset = self.create_asset(
            value=100000,
            periodicity='yearly',
            periods=5,
            method='degressive',
            method_progress_factor=0.35,
            acquisition_date='2022-01-01',
            prorata_computation_type='constant_periods'
        )
        asset.compute_depreciation_board()
        self.assertEqual(asset.state, 'draft')
        self.assertEqual(asset.book_value, 100000)
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=35000.00, remaining_value=65000.00, depreciated_value=35000.00, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=22750.00, remaining_value=42250.00, depreciated_value=57750.00, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=14787.50, remaining_value=27462.50, depreciated_value=72537.50, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=13731.25, remaining_value=13731.25, depreciated_value=86268.75, state='draft'),
            self._get_depreciation_move_values(date='2026-12-31', depreciation_value=13731.25, remaining_value=0.00, depreciated_value=100000.00, state='draft'),
        ])

    def test_degressive_5_years_from_middle_of_year(self):
        asset = self.create_asset(
            value=100000,
            periodicity='yearly',
            periods=5,
            method='degressive',
            method_progress_factor=0.35,
            acquisition_date='2022-07-01',
            prorata_computation_type='constant_periods'
        )
        asset.compute_depreciation_board()
        self.assertEqual(asset.state, 'draft')
        self.assertEqual(asset.book_value, 100000)
        self.assertRecordValues(asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=17500.00, remaining_value=82500.00, depreciated_value=17500.00, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=28875.00, remaining_value=53625.00, depreciated_value=46375.00, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=18768.75, remaining_value=34856.25, depreciated_value=65143.75, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=13942.50, remaining_value=20913.75, depreciated_value=79086.25, state='draft'),
            self._get_depreciation_move_values(date='2026-12-31', depreciation_value=13942.50, remaining_value=6971.25, depreciated_value=93028.75, state='draft'),
            self._get_depreciation_move_values(date='2027-12-31', depreciation_value=6971.25, remaining_value=0.00, depreciated_value=100000.00, state='draft'),
        ])

    def test_compute_board_in_mass(self):
        book = self.create_asset(value=35, periodicity="monthly", periods=2, method="linear", salvage_value=0)
        shelf = self.create_asset(value=250, periodicity="monthly", periods=8, method="linear", salvage_value=0)
        screw = self.create_asset(value=1, periodicity="monthly", periods=1, method="linear", salvage_value=0)

        (book + screw).validate()
        (book + shelf + screw).compute_depreciation_board()

        self.assertRecordValues(book.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=17.5, remaining_value=17.5, depreciated_value=17.5, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=17.5, remaining_value=0, depreciated_value=35, state='posted'),
        ])

        self.assertRecordValues(shelf.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=31.25, remaining_value=218.75, depreciated_value=31.25, state='draft'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=31.25, remaining_value=187.5, depreciated_value=62.5, state='draft'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=31.25, remaining_value=156.25, depreciated_value=93.75, state='draft'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=31.25, remaining_value=125, depreciated_value=125, state='draft'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=31.25, remaining_value=93.75, depreciated_value=156.25, state='draft'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=31.25, remaining_value=62.5, depreciated_value=187.5, state='draft'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=31.25, remaining_value=31.25, depreciated_value=218.75, state='draft'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=31.25, remaining_value=0, depreciated_value=250, state='draft'),
        ])

        self.assertRecordValues(screw.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=1, remaining_value=0, depreciated_value=1, state='posted'),
        ])
    def test_copy_prorata_date(self):
        """ Verifies that prorata date and acquisition date are copied when duplicate an asset
            For this test, the prorata computation type is set to None.
            The idea is of this test is to verify that we do copy prorata date.
        """
        old_car_asset = self.create_asset(
            value=60000,
            periodicity='yearly',
            periods=5,
            method='linear',
            salvage_value=0,

        )
        old_car_asset.validate()

        self.assertEqual(old_car_asset.state, 'open')
        self.assertEqual(old_car_asset.book_value, 36000)
        self.assertEqual(old_car_asset.acquisition_date, fields.Date.from_string('2020-02-01'))
        self.assertEqual(old_car_asset.prorata_date, fields.Date.from_string('2020-01-01'))
        self.assertRecordValues(old_car_asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=12000, remaining_value=48000, depreciated_value=12000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=24000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        new_car_asset = old_car_asset.copy()
        new_car_asset.original_value = 60000
        new_car_asset.validate()

        self.assertEqual(new_car_asset.state, 'open')
        self.assertEqual(new_car_asset.book_value, 36000)
        self.assertEqual(new_car_asset.acquisition_date, fields.Date.from_string('2020-02-01'))
        self.assertEqual(new_car_asset.prorata_date, fields.Date.from_string('2020-01-01'))
        self.assertRecordValues(new_car_asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=12000, remaining_value=48000, depreciated_value=12000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=24000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_change_computation_method_before_lock_date(self):
        """Test that we can change the computation method when there are draft moves before the lock date.
        """
        self.car.company_id.fiscalyear_lock_date = '2022-06-30'
        self.car.compute_depreciation_board()

        self.assertEqual(self.car.state, 'draft')
        self.assertEqual(self.car.book_value, 60000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=12000, remaining_value=48000, depreciated_value=12000, state='draft'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=24000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        # Change the computation type
        self.car.prorata_computation_type = 'constant_periods'
        self.car.prorata_date = '2021-01-01'
        self.car.compute_depreciation_board()

        self.assertEqual(self.car.state, 'draft')
        self.assertEqual(self.car.book_value, 60000)
        self.assertRecordValues(self.car.depreciation_move_ids.sorted(lambda m: (m.date, m.id)), [
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=48000, depreciated_value=12000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=24000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_post_moves_after_lock_date(self):
        """Test that we can change the computation method when there are draft moves before the lock date.
        """
        self.car.company_id.fiscalyear_lock_date = '2021-06-30'
        self.car.compute_depreciation_board()

        self.assertEqual(self.car.state, 'draft')
        self.assertEqual(self.car.book_value, 60000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=12000, remaining_value=48000, depreciated_value=12000, state='draft'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=24000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=12000, remaining_value=48000, depreciated_value=12000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=24000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_assets_one_complete_period(self):
        """Test the depreciation move value in case of having just one complete period (year or month) asset."""
        datas = [
            ('monthly', '2022-01-31', 'linear'),
            ('monthly', '2022-01-31', 'degressive'),
            ('monthly', '2022-01-31', 'degressive_then_linear'),
            ('yearly', '2022-12-31', 'linear'),
            ('yearly', '2022-12-31', 'degressive'),
            ('yearly', '2022-12-31', 'degressive_then_linear'),
        ]
        for periodicity, end_depreciation_date, method in datas:
            with self.subTest(period=periodicity, method=method, end_depreciation_date=end_depreciation_date):
                asset = self.create_asset(
                    value=1000,
                    periodicity=periodicity,
                    periods=1,
                    method=method,
                    acquisition_date='2022-01-01',
                    prorata_date='2022-01-01',
                    prorata_computation_type='constant_periods',
                    account_depreciation_id=self.company_data['default_account_assets'].id,
                )

                asset.compute_depreciation_board()
                self.assertEqual(asset.state, 'draft')
                self.assertRecordValues(asset.depreciation_move_ids, [
                    self._get_depreciation_move_values(date=end_depreciation_date, depreciation_value=1000.0, remaining_value=0.0, depreciated_value=1000.0, state='draft'),
                ])
                asset.validate()
                self.assertEqual(asset.state, 'open')
