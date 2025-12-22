# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('fi')
    def _get_fi_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'account_1701',
            'property_account_payable_id': 'account_2871',
            'property_account_expense_categ_id': 'account_4000',
            'property_account_income_categ_id': 'account_3000',
            }

    @template('fi', 'res.company')
    def _get_fi_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.fi',
                'bank_account_code_prefix': '1921',
                'cash_account_code_prefix': '1910',
                'transfer_account_code_prefix': '1950',
                'account_default_pos_receivable_account_id': 'account_1701',
                'income_currency_exchange_account_id': 'account_3500',
                'expense_currency_exchange_account_id': 'account_4380',
                'account_journal_early_pay_discount_loss_account_id': 'account_4230',
                'account_journal_early_pay_discount_gain_account_id': 'account_3500',
                'account_sale_tax_id': 'tax_dom_sales_goods_25_5',
                'account_purchase_tax_id': 'tax_dom_purchase_goods_25_5',
            },
        }
