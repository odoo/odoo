# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('my')
    def _get_my_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_my_1240',
            'property_account_payable_id': 'l10n_my_2211',
            'code_digits': '6',
        }

    @template('my', 'res.company')
    def _get_my_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.my',
                'bank_account_code_prefix': '1200',
                'cash_account_code_prefix': '1210',
                'transfer_account_code_prefix': '111220',
                'account_default_pos_receivable_account_id': 'l10n_my_1243',
                'income_currency_exchange_account_id': 'l10n_my_4240',
                'expense_currency_exchange_account_id': 'l10n_my_5240',
                'account_sale_tax_id': 'l10n_my_tax_sale_10',
                'income_account_id': 'l10n_my_41',
                'expense_account_id': 'l10n_my_51',
                'tax_calculation_rounding_method': 'round_per_line',
            },
        }
