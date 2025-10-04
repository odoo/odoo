# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hr_kuna')
    def _get_hr_kuna_template_data(self):
        return {
            'name': 'RRIF-ov računski plan za poduzetnike',
            'code_digits': '0',
            'use_storno_accounting': True,
            'property_account_receivable_id': 'kp_rrif1200',
            'property_account_payable_id': 'kp_rrif2200',
            'property_account_expense_categ_id': 'kp_rrif4199',
            'property_account_income_categ_id': 'kp_rrif7500',
        }

    @template('hr_kuna', 'res.company')
    def _get_hr_kuna_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.hr',
                'bank_account_code_prefix': '101',
                'cash_account_code_prefix': '102',
                'transfer_account_code_prefix': '1009',
                'account_default_pos_receivable_account_id': 'kp_rrif1213',
                'income_currency_exchange_account_id': 'kp_rrif1050',
                'expense_currency_exchange_account_id': 'kp_rrif4754',
            },
        }
