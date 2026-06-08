# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('eg')
    def _get_eg_template_data(self):
        return {
            'code_digits': '6',
            }

    @template('eg', 'res.company')
    def _get_eg_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.eg',
                'bank_account_code_prefix': '160',
                'transfer_account_id': 'egy_account_160700',
                'account_default_pos_receivable_account_id': 'egy_account_150200',
                'income_currency_exchange_account_id': 'egy_account_510200',
                'expense_currency_exchange_account_id': 'egy_account_430700',
                'account_journal_suspense_account_id': 'egy_account_160103',
                'account_journal_early_pay_discount_loss_account_id': 'egy_account_430800',
                'account_journal_early_pay_discount_gain_account_id': 'egy_account_510400',
                'default_cash_difference_income_account_id': 'egy_account_990100',
                'default_cash_difference_expense_account_id': 'egy_account_990200',
                'account_sale_tax_id': 'eg_standard_sale_14',
                'account_purchase_tax_id': 'eg_standard_purchase_14',
                'expense_account_id': 'egy_account_424800',
                'income_account_id': 'egy_account_500100',
                'receivable_account_id': 'egy_account_150100',
                'payable_account_id': 'egy_account_220100',
                'tax_calculation_rounding_method': 'round_per_line',
                'account_cash_basis_base_account_id': 'egy_account_210802',
                'account_stock_valuation_id': 'egy_account_120100',
                'deferred_expense_account_id': 'egy_account_131300',
                'deferred_revenue_account_id': 'egy_account_230100',
            },
        }

    @template('eg', 'account.journal')
    def _get_eg_account_journal(self):
        """ If EGYPT chart, we add 2 new journals TA and IFRS"""
        return {
            "tax_adjustment": {
                "name": "Tax Adjustments",
                "code": "TA",
                "type": "general",
                "sequence": 10,
                "show_on_dashboard": True,
            },
            "ifrs": {
                "name": "IFRS 16",
                "code": "IFRS",
                "type": "general",
                "show_on_dashboard": True,
                "sequence": 11,
            },
            'bank': {
                'default_account_id': 'egy_account_160100',
            },
        }

    @template('eg', 'account.account')
    def _get_eg_account_account(self):
        return {
            'egy_account_110800': {'asset_depreciation_account_id': 'egy_account_110800', 'asset_expense_account_id': 'egy_account_424000'},
            'egy_account_111000': {'asset_depreciation_account_id': 'egy_account_111000', 'asset_expense_account_id': 'egy_account_424100'},
            'egy_account_111200': {'asset_depreciation_account_id': 'egy_account_111200', 'asset_expense_account_id': 'egy_account_424200'},
            'egy_account_110200': {'asset_depreciation_account_id': 'egy_account_110200', 'asset_expense_account_id': 'egy_account_411902'},
            'egy_account_110300': {'asset_depreciation_account_id': 'egy_account_110300', 'asset_expense_account_id': 'egy_account_424300'},
            'egy_account_110400': {'asset_depreciation_account_id': 'egy_account_110400', 'asset_expense_account_id': 'egy_account_424400'},
            'egy_account_111600': {'asset_depreciation_account_id': 'egy_account_111600', 'asset_expense_account_id': 'egy_account_424500'},
            'egy_account_110500': {'asset_depreciation_account_id': 'egy_account_110500', 'asset_expense_account_id': 'egy_account_424600'},
            'egy_account_120100': {
                'account_stock_expense_id': 'egy_account_400300',
                'account_stock_variation_id': 'egy_account_400400',
            },
        }

    def _create_outstanding_accounts(self, company, bank_prefix, code_digits):
        if company.chart_template != 'eg':
            return super()._create_outstanding_accounts(company, bank_prefix, code_digits)

        parent = self.ref('egy_account_150000')
        accounts_data_no_fields = {
            'account_journal_payment_debit_account_id': {
                'name': self.env._("Outstanding Receipts"),
                'parent_id': parent.id,
                'prefix': '150',
                'code_digits': code_digits,
                'account_type': 'asset_current',
                'reconcile': True,
            },
            'account_journal_payment_credit_account_id': {
                'name': self.env._("Outstanding Payments"),
                'parent_id': parent.id,
                'prefix': '150',
                'code_digits': code_digits,
                'account_type': 'asset_current',
                'reconcile': True,
            },
        }
        self.env['account.account']._load_records([
            {
                'xml_id': self.company_xmlid(xml_id, company),
                'values': values,
                'noupdate': True,
            }
            for xml_id, values in accounts_data_no_fields.items()
        ])
