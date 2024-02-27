# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ae')
    def _get_ae_template_data(self):
        return {
            'property_account_receivable_id': 'uae_account_102011',
            'property_account_payable_id': 'uae_account_201002',
            'property_account_expense_categ_id': 'uae_account_400001',
            'property_account_income_categ_id': 'uae_account_500001',
            'code_digits': '6',
        }

    @template('ae', 'res.company')
    def _get_ae_res_company(self):
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

    @template('ae', 'account.account')
    def _get_ae_account_account(self):
        return {
            "uae_account_100101": {
                'allowed_journal_ids': [Command.link('ifrs16')],
            },
            "uae_account_100102": {
                'allowed_journal_ids': [Command.link('ifrs16')],
            },
            "uae_account_400070": {
                'allowed_journal_ids': [Command.link('ifrs16')],
            },
        }
