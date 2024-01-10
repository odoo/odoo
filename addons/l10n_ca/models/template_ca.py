# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ca')
    def _get_ca_template_data(self):
        return {
            'property_account_receivable_id': 'chart1151_en',
            'property_account_payable_id': 'chart2111_en',
            'property_account_income_categ_id': 'chart411_en',
            'property_account_expense_categ_id': 'chart5111_en',
            'property_stock_account_input_categ_id': 'chart2171_en',
            'property_stock_account_output_categ_id': 'chart1145_en',
            'property_stock_valuation_account_id': 'chart1141_en',
        }

    @template('ca', 'res.company')
    def _get_ca_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.ca',
                'bank_account_code_prefix': '112',
                'cash_account_code_prefix': '111',
                'transfer_account_code_prefix': '113',
                'account_default_pos_receivable_account_id': 'chart11511_en',
                'income_currency_exchange_account_id': 'chart42_en',
                'expense_currency_exchange_account_id': 'chart55_en',
                'account_journal_early_pay_discount_loss_account_id': 'chart550001_en',
                'account_journal_early_pay_discount_gain_account_id': 'chart420001_en',
            },
        }
