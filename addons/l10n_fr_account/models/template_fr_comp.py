from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('fr_comp')
    def _get_fr_comp_template_data(self):
        return {
            'name': self.env._("Companies accounting plan"),
            'parent': 'fr',
            'sequence': 0,
            'code_digits': 6,
            'property_account_receivable_id': 'fr_pcg_recv',
            'property_account_payable_id': 'fr_pcg_pay',
            'property_account_downpayment_categ_id': 'pcg_4191',
        }

    @template('fr_comp', 'res.company')
    def _get_fr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.fr',
                'bank_account_code_prefix': '512',
                'cash_account_code_prefix': '53',
                'transfer_account_code_prefix': '58',
                'account_default_pos_receivable_account_id': 'fr_pcg_recv_pos',
                'income_currency_exchange_account_id': 'pcg_766',
                'expense_currency_exchange_account_id': 'pcg_666',
                'account_journal_suspense_account_id': 'pcg_471',
                'account_journal_early_pay_discount_loss_account_id': 'pcg_665',
                'account_journal_early_pay_discount_gain_account_id': 'pcg_765',
                'deferred_expense_account_id': 'pcg_486',
                'deferred_revenue_account_id': 'pcg_487',
                'l10n_fr_rounding_difference_loss_account_id': 'pcg_4768',
                'l10n_fr_rounding_difference_profit_account_id': 'pcg_4778',
                'account_sale_tax_id': 'tva_normale',
                'account_purchase_tax_id': 'tva_acq_normale',
                'expense_account_id': 'pcg_607_account',
                'income_account_id': 'pcg_707_account',
                'downpayment_account_id': 'pcg_4191',
                'account_stock_valuation_id': 'pcg_31_account',
            },
        }

    @template('fr_comp', 'account.account')
    def _get_fr_comp_account_account(self):
        return {
            'pcg_2011': {
                'asset_depreciation_account_id': 'pcg_2801',
                'asset_expense_account_id': 'pcg_68111',
            },
            'pcg_203': {
                'asset_depreciation_account_id': 'pcg_2801',
                'asset_expense_account_id': 'pcg_68111',
            },
            'pcg_205': {
                'asset_depreciation_account_id': 'pcg_2805',
                'asset_expense_account_id': 'pcg_68111',
            },
            'pcg_206': {
                'asset_depreciation_account_id': 'pcg_2806',
                'asset_expense_account_id': 'pcg_68111',
            },
            'pcg_207': {
                'asset_depreciation_account_id': 'pcg_2807',
                'asset_expense_account_id': 'pcg_68111',
            },
            'pcg_208': {
                'asset_depreciation_account_id': 'pcg_2808',
                'asset_expense_account_id': 'pcg_68111',
            },
            'pcg_2113': {
                'asset_depreciation_account_id': 'pcg_2813',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_212': {
                'asset_depreciation_account_id': 'pcg_2812',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2131': {
                'asset_depreciation_account_id': 'pcg_2813',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2135': {
                'asset_depreciation_account_id': 'pcg_2813',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2138_account': {
                'asset_depreciation_account_id': 'pcg_2813',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_214': {
                'asset_depreciation_account_id': 'pcg_2814',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_21511': {
                'asset_depreciation_account_id': 'pcg_2815',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_21514': {
                'asset_depreciation_account_id': 'pcg_2815',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_21531': {
                'asset_depreciation_account_id': 'pcg_2815',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_21534': {
                'asset_depreciation_account_id': 'pcg_2815',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2154': {
                'asset_depreciation_account_id': 'pcg_2815',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2155': {
                'asset_depreciation_account_id': 'pcg_2815',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2157': {
                'asset_depreciation_account_id': 'pcg_2815',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2181': {
                'asset_depreciation_account_id': 'pcg_2818',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2182': {
                'asset_depreciation_account_id': 'pcg_2818',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2183': {
                'asset_depreciation_account_id': 'pcg_2818',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2184': {
                'asset_depreciation_account_id': 'pcg_2818',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2185': {
                'asset_depreciation_account_id': 'pcg_2818',
                'asset_expense_account_id': 'pcg_68112',
            },
            'pcg_2186': {
                'asset_depreciation_account_id': 'pcg_2818',
                'asset_expense_account_id': 'pcg_68112',
            },
        }
