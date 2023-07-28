# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pt')
    def _get_pt_template_data(self):
        return {
            'property_account_receivable_id': 'chart_2111',
            'property_account_payable_id': 'chart_2211',
            'property_account_income_categ_id': 'chart_711',
            'property_account_expense_categ_id': 'chart_311',
            'property_tax_payable_account_id': 'chart_2436',
            'property_tax_receivable_account_id': 'chart_2437',
        }

    @template('pt', 'res.company')
    def _get_pt_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pt',
                'bank_account_code_prefix': '12',
                'cash_account_code_prefix': '11',
                'transfer_account_code_prefix': '15',
                'account_default_pos_receivable_account_id': 'chart_2117',
                'income_currency_exchange_account_id': 'chart_7861',
                'expense_currency_exchange_account_id': 'chart_6863',
                'account_journal_early_pay_discount_loss_account_id': 'chart_682',
                'account_journal_early_pay_discount_gain_account_id': 'chart_728',
                'account_sale_tax_id': 'iva_pt_sale_normal',
                'account_purchase_tax_id': 'iva_pt_purchase_normal',
            },
        }
