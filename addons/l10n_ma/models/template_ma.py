# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ma')
    def _get_ma_template_data(self):
        return {
            'property_account_receivable_id': 'pcg_34211',
            'property_account_payable_id': 'pcg_4411',
            'property_account_income_categ_id': 'pcg_7111',
            'property_account_expense_categ_id': 'pcg_6111',
            'code_digits': '6',
            'display_invoice_amount_total_words': True,
        }

    @template('ma', 'res.company')
    def _get_ma_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ma',
                'bank_account_code_prefix': '5141',
                'cash_account_code_prefix': '5161',
                'transfer_account_code_prefix': '5115',
                'account_default_pos_receivable_account_id': 'pcg_3489',
                'income_currency_exchange_account_id': 'pcg_733',
                'expense_currency_exchange_account_id': 'pcg_633',
            },
        }
