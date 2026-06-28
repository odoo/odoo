# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ae')
    def _get_ae_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('ae', 'res.company')
    def _get_ae_res_company(self):
        sales_tax_xmlid = {
            'AZ': 'uae_sale_tax_5_abu_dhabi',
            'AJ': 'uae_sale_tax_5_ajman',
            'DU': 'uae_sale_tax_5_dubai',
            'FU': 'uae_sale_tax_5_fujairah',
            'RK': 'uae_sale_tax_5_ras_al_khaima',
            'SH': 'uae_sale_tax_5_sharjah',
            'UQ': 'uae_sale_tax_5_umm_al_quwain',
        }.get(self.env.company.state_id.code, 'uae_sale_tax_5_dubai')
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ae',
                'bank_account_code_prefix': '1601',
                'cash_account_code_prefix': '105',
                'transfer_account_code_prefix': '1701',
                'account_default_pos_receivable_account_id': 'uae_account_150200',
                'income_currency_exchange_account_id': 'uae_account_510200',
                'expense_currency_exchange_account_id': 'uae_account_430700',
                'account_journal_early_pay_discount_loss_account_id': 'uae_account_430800',
                'account_journal_early_pay_discount_gain_account_id': 'uae_account_510500',
                'account_sale_tax_id': sales_tax_xmlid,
                'account_purchase_tax_id': 'uae_purchase_tax_5',
                'expense_account_id': 'uae_account_400100',
                'income_account_id': 'uae_account_500100',
                'receivable_account_id': 'uae_account_150100',
                'payable_account_id': 'uae_account_230100',
                'tax_calculation_rounding_method': 'round_per_line',
                'account_stock_valuation_id': 'uae_account_120100',
            },
        }

    @template('ae', 'account.journal')
    def _get_ae_account_journal(self):
        """ If UAE chart, we add 2 new journals TA and IFRS"""
        return {
            "tax_adjustment":{
                "name": "Tax Adjustments",
                "code": "TA",
                "type": "general",
                "show_on_dashboard": True,
                "sequence": 10,
            },
            "ifrs16": {
                "name": "IFRS 16",
                "code": "IFRS",
                "type": "general",
                "show_on_dashboard": True,
                "sequence": 11,
            },
            "bank": {
                "default_account_id": "uae_account_160100",
            },
        }

    @template('ae', 'account.fiscal.position')
    def _get_ae_account_fiscal_position(self):
        fiscal_position_xmlid = {
            'AZ': 'account_fiscal_position_abu_dhabi',
            'AJ': 'account_fiscal_position_ajman',
            'DU': 'account_fiscal_position_dubai',
            'FU': 'account_fiscal_position_fujairah',
            'RK': 'account_fiscal_position_ras_al_khaima',
            'SH': 'account_fiscal_position_sharjah',
            'UQ': 'account_fiscal_position_umm_al_quwain',
        }.get(self.env.company.state_id.code, 'account_fiscal_position_dubai')
        return {
            fiscal_position_xmlid: {
                'sequence': 1,
            }
        }

    @template('ae', 'account.account')
    def _get_ae_account_account(self):
        return {
            'uae_account_110800': {'asset_depreciation_account_id': 'uae_account_110800', 'asset_expense_account_id': 'uae_account_424100'},
            'uae_account_111000': {'asset_depreciation_account_id': 'uae_account_111000', 'asset_expense_account_id': 'uae_account_424200'},
            'uae_account_111200': {'asset_depreciation_account_id': 'uae_account_111200', 'asset_expense_account_id': 'uae_account_424300'},
            'uae_account_110200': {'asset_depreciation_account_id': 'uae_account_110200', 'asset_expense_account_id': 'uae_account_424400'},
            'uae_account_110300': {'asset_depreciation_account_id': 'uae_account_110300', 'asset_expense_account_id': 'uae_account_424500'},
            'uae_account_110400': {'asset_depreciation_account_id': 'uae_account_110400', 'asset_expense_account_id': 'uae_account_424600'},
            'uae_account_111600': {'asset_depreciation_account_id': 'uae_account_111600', 'asset_expense_account_id': 'uae_account_424700'},
            'uae_account_110500': {'asset_depreciation_account_id': 'uae_account_110500', 'asset_expense_account_id': 'uae_account_424800'},
            'uae_account_120100': {
                'account_stock_variation_id': 'uae_account_400100',
            },
        }
