from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestAccountAssetCommon(AccountTestInvoicingCommon):

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
