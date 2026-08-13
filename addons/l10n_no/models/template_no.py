# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('no')
    def _get_no_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'chart1500',
            'property_account_payable_id': 'chart2400',
            'property_account_expense_categ_id': 'chart4000',
            'property_account_income_categ_id': 'chart3000',
        }

    @template('no', 'res.company')
    def _get_no_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.no',
                'bank_account_code_prefix': '1920',
                'cash_account_code_prefix': '1900',
                'transfer_account_code_prefix': '1940',
                'account_default_pos_receivable_account_id': 'chart1500',
                'income_currency_exchange_account_id': 'chart8060',
                'expense_currency_exchange_account_id': 'chart8160',
                'account_journal_early_pay_discount_loss_account_id': 'chart4372',
                'account_journal_early_pay_discount_gain_account_id': 'chart3082',
                'account_sale_tax_id': 'tax3',
                'account_purchase_tax_id': 'tax2',
            },
        }
