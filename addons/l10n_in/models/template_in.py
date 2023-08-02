# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in')
    def _get_in_template_data(self):
        return {
            'property_account_receivable_id': 'p10040',
            'property_account_payable_id': 'p11211',
            'property_account_expense_categ_id': 'p2107',
            'property_account_income_categ_id': 'p20011',
            'property_tax_payable_account_id': 'p11239',
            'property_tax_receivable_account_id': 'p10059',
            'code_digits': '6',
            'display_invoice_amount_total_words': True,
        }

    @template('in', 'res.company')
    def _get_in_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.in',
                'bank_account_code_prefix': '1002',
                'cash_account_code_prefix': '1001',
                'transfer_account_code_prefix': '1008',
                'account_default_pos_receivable_account_id': 'p10041',
                'income_currency_exchange_account_id': 'p2013',
                'expense_currency_exchange_account_id': 'p2117',
                'account_journal_early_pay_discount_loss_account_id': 'p2132',
                'account_journal_early_pay_discount_gain_account_id': '2012',
                'account_opening_date': fields.Date.context_today(self).replace(month=4, day=1),
                'fiscalyear_last_month': '3',
                'account_sale_tax_id': 'igst_sale_18',
                'account_purchase_tax_id': 'igst_purchase_18',
            },
        }
