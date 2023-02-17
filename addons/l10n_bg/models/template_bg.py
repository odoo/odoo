# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('bg')
    def _get_bg_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_bg_411',
            'property_account_payable_id': 'l10n_bg_401',
            'property_account_expense_categ_id': 'l10n_bg_601',
            'property_account_income_categ_id': 'l10n_bg_701',
            'code_digits': '6',
        }

    @template('bg', 'res.company')
    def _get_bg_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.bg',
                'bank_account_code_prefix': '503',
                'cash_account_code_prefix': '501',
                'transfer_account_code_prefix': '430',
                'income_currency_exchange_account_id': 'l10n_bg_624',
                'expense_currency_exchange_account_id': 'l10n_bg_624',
            },
        }
