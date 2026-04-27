from freezegun import freeze_time

from odoo import fields

from odoo.tests.common import tagged
from odoo.addons.account_asset.tests.common import TestAccountAssetCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestIndianAccountAsset(TestAccountAssetCommon):

    @classmethod
    @TestAccountAssetCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()

    @freeze_time("2024-12-01")
    def test_degressive_3_years_no_depreciated_amount(self):
        in_asset = self.create_asset(value=100000, periodicity="yearly", periods=3, method='degressive', acquisition_date="2023-04-01", salvage_value=5000, method_progress_factor=0.6316)
        in_asset.validate()

        self.assertEqual(in_asset.state, 'open')
        self.assertEqual(in_asset.l10n_in_value_residual, 31840.0)
        self.assertRecordValues(in_asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=63160, remaining_value=36840, depreciated_value=63160, state='posted'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=23268.14, remaining_value=13571.86, depreciated_value=86428.14, state='draft'),
            self._get_depreciation_move_values(date='2026-03-31', depreciation_value=8571.86, remaining_value=5000, depreciated_value=95000, state='draft'),
        ])

    @freeze_time("2024-12-01")
    def test_degressive_3_years(self):
        in_asset = self.create_asset(value=100000, periodicity="yearly", periods=3, method='degressive', acquisition_date="2023-04-01", salvage_value=5000, method_progress_factor=0.6316, already_depreciated_amount_import=30000)
        in_asset.validate()

        self.assertEqual(in_asset.state, 'open')
        self.assertEqual(in_asset.l10n_in_value_residual, 31840.0)
        self.assertRecordValues(in_asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=33160, remaining_value=36840, depreciated_value=63160, state='posted'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=23268.14, remaining_value=13571.86, depreciated_value=86428.14, state='draft'),
            self._get_depreciation_move_values(date='2026-03-31', depreciation_value=8571.86, remaining_value=5000, depreciated_value=95000, state='draft'),
        ])

    @freeze_time("2024-12-01")
    def test_degressive_negative_3_years(self):
        in_asset = self.create_asset(value=-100000, periodicity="yearly", periods=3, method='degressive', acquisition_date="2023-04-01", salvage_value=-5000, method_progress_factor=0.6316, already_depreciated_amount_import=-30000)
        in_asset.validate()

        self.assertEqual(in_asset.state, 'open')
        self.assertEqual(in_asset.l10n_in_value_residual, -31840.0)
        self.assertRecordValues(in_asset.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=-33160, remaining_value=-36840, depreciated_value=-63160, state='posted'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=-23268.14, remaining_value=-13571.86, depreciated_value=-86428.14, state='draft'),
            self._get_depreciation_move_values(date='2026-03-31', depreciation_value=-8571.86, remaining_value=-5000, depreciated_value=-95000, state='draft'),
        ])

    @freeze_time("2024-12-01")
    def test_degressive_5_years_then_increase(self):
        in_asset = self.create_asset(value=100000, periodicity="yearly", periods=5, method='degressive', acquisition_date="2023-04-01", salvage_value=5000, method_progress_factor=0.4507, already_depreciated_amount_import=45070)
        in_asset.validate()
        self.env['asset.modify'].create({
            'asset_id': in_asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2024-03-31"),
            'l10n_in_value_residual': 2 * in_asset.l10n_in_value_residual,
            'salvage_value': 2 * in_asset.salvage_value,
            "account_asset_counterpart_id": self.company_data['default_account_expense'].copy().id,
        }).modify()

        self.assertRecordValues(in_asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=24756.95, depreciated_value=69826.95, remaining_value=30173.05, state='draft'),
            self._get_depreciation_move_values(date='2026-03-31', depreciation_value=13598.99, depreciated_value=83425.94, remaining_value=16574.06, state='draft'),
            self._get_depreciation_move_values(date='2027-03-31', depreciation_value=7469.93, depreciated_value=90895.87, remaining_value=9104.13, state='draft'),
            self._get_depreciation_move_values(date='2028-03-31', depreciation_value=4104.13, depreciated_value=95000.00, remaining_value=5000.00, state='draft'),
        ])
        self.assertEqual(in_asset.children_ids[0].original_value, 54930.00)
        self.assertEqual(in_asset.children_ids[0].salvage_value, 5000.00)
        self.assertEqual(in_asset.children_ids[0].l10n_in_value_residual, 49930.00)
        self.assertRecordValues(in_asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=24756.95, depreciated_value=24756.95, remaining_value=30173.05, state='draft'),
            self._get_depreciation_move_values(date='2026-03-31', depreciation_value=13598.99, depreciated_value=38355.94, remaining_value=16574.06, state='draft'),
            self._get_depreciation_move_values(date='2027-03-31', depreciation_value=7469.93, depreciated_value=45825.87, remaining_value=9104.13, state='draft'),
            self._get_depreciation_move_values(date='2028-03-31', depreciation_value=4104.13, depreciated_value=49930.00, remaining_value=5000.00, state='draft'),
        ])

    @freeze_time("2024-12-01")
    def test_degressive_5_years_then_decrease(self):
        in_asset = self.create_asset(value=100000, periodicity="yearly", periods=5, method='degressive', acquisition_date="2023-04-01", salvage_value=5000, method_progress_factor=0.4507, already_depreciated_amount_import=45070)
        in_asset.validate()
        self.env['asset.modify'].create({
            'asset_id': in_asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2024-03-31"),
            'l10n_in_value_residual': in_asset.l10n_in_value_residual - 500,
            'salvage_value': in_asset.salvage_value - 500,
        }).modify()

        self.assertEqual(in_asset.salvage_value, 4500.00)
        self.assertEqual(in_asset.l10n_in_value_residual, 49430.00)
        self.assertRecordValues(in_asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1000.00, depreciated_value=46070.00, remaining_value=53930.00, state='posted'),
            self._get_depreciation_move_values(date='2026-03-31', depreciation_value=24058.68, depreciated_value=70128.68, remaining_value=29871.32, state='draft'),
            self._get_depreciation_move_values(date='2027-03-31', depreciation_value=13463.00, depreciated_value=83591.68, remaining_value=16408.32, state='draft'),
            self._get_depreciation_move_values(date='2028-03-31', depreciation_value=11908.32, depreciated_value=95500.00, remaining_value=4500.00, state='draft'),
        ])
