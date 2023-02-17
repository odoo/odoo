# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gr')
    def _get_gr_template_data(self):
        return {
            'property_account_receivable_id': 'chartgr_30_00',
            'property_account_payable_id': 'chartgr_50_00',
            'property_account_expense_categ_id': 'chartgr_64_98',
            'property_account_income_categ_id': 'chartgr_71_00',
            'code_digits': '6',
        }

    @template('gr', 'res.company')
    def _get_gr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.gr',
                'bank_account_code_prefix': '38',
                'cash_account_code_prefix': '38',
                'transfer_account_code_prefix': '38.07',
                'account_default_pos_receivable_account_id': 'chartgr_30_00_01',
                'income_currency_exchange_account_id': 'chartgr_79_79',
                'expense_currency_exchange_account_id': 'chartgr_64_98_06',
            },
        }
