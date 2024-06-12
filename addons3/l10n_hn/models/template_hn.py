# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hn')
    def _get_hn_template_data(self):
        return {
            'property_account_receivable_id': 'cta110201',
            'property_account_payable_id': 'cta210101',
            'property_account_income_categ_id': 'cta410101',
            'property_account_expense_categ_id': 'cta510101',
            'code_digits': '9',
        }

    @template('hn', 'res.company')
    def _get_hn_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.hn',
                'bank_account_code_prefix': '1.1.01.',
                'cash_account_code_prefix': '1.1.01.',
                'transfer_account_code_prefix': '1.1.01.00',
                'account_default_pos_receivable_account_id': 'cta110205',
                'income_currency_exchange_account_id': 'cta410103',
                'expense_currency_exchange_account_id': 'cta710101',
                'account_journal_early_pay_discount_loss_account_id': 'cta620202',
                'account_journal_early_pay_discount_gain_account_id': 'cta420102',
                'account_sale_tax_id': 'impuestos_plantilla_isv_por_pagar',
                'account_purchase_tax_id': 'impuestos_plantilla_isv_por_cobrar',
            },
        }
