# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


_AE_STATE_MAPPING = {
    'AZ': 'abu_dhabi',
    'AJ': 'ajman',
    'DU': 'dubai',
    'FU': 'fujairah',
    'RK': 'ras_al_khaima',
    'SH': 'sharjah',
    'UQ': 'umm_al_quwain',
}


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ae')
    def _get_ae_template_data(self):
        return {
            'property_account_receivable_id': 'uae_account_102011',
            'property_account_payable_id': 'uae_account_201002',
            'code_digits': '6',
        }

    @template('ae', 'res.company')
    def _get_ae_res_company(self):
        state_name = _AE_STATE_MAPPING.get(self.env.company.state_id.code, 'dubai')
        sales_tax_xmlid = f'uae_sale_tax_5_{state_name}'
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ae',
                'bank_account_code_prefix': '101',
                'cash_account_code_prefix': '105',
                'transfer_account_code_prefix': '100',
                'account_default_pos_receivable_account_id': 'uae_account_102012',
                'income_currency_exchange_account_id': 'uae_account_500011',
                'expense_currency_exchange_account_id': 'uae_account_400053',
                'account_journal_early_pay_discount_loss_account_id': 'uae_account_400071',
                'account_journal_early_pay_discount_gain_account_id': 'uae_account_500014',
                'account_sale_tax_id': sales_tax_xmlid,
                'account_purchase_tax_id': 'uae_purchase_tax_5',
                'expense_account_id': 'uae_account_400001',
                'income_account_id': 'uae_account_500001',
                'tax_calculation_rounding_method': 'round_per_line',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'uae_account_131100',
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
                "sequence": 1,
            },
            "ifrs16": {
                "name": "IFRS 16",
                "code": "IFRS",
                "type": "general",
                "show_on_dashboard": True,
                "sequence": 10,
            }
        }

    @template('ae', 'account.fiscal.position')
    def _get_ae_account_fiscal_position(self):
        state_name = _AE_STATE_MAPPING.get(self.env.company.state_id.code, 'dubai')
        fiscal_position_xmlid = f'account_fiscal_position_{state_name}'
        return {
            fiscal_position_xmlid: {
                'sequence': 1,
            }
        }

    @template('ae', 'account.account')
    def _get_ae_account_account(self):
        return {
            'uae_account_131100': {
                'account_stock_variation_id': 'uae_account_400001',
            },
        }
