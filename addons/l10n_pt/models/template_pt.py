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
        }

    @template('pt', 'res.company')
    def _get_pt_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pt',
                'bank_account_code_prefix': '12',
                'cash_account_code_prefix': '11',
                'transfer_account_code_prefix': '1431',
                'account_default_pos_receivable_account_id': 'chart_2117',
                'income_currency_exchange_account_id': 'chart_7861',
                'expense_currency_exchange_account_id': 'chart_6863',
                'tax_calculation_rounding_method': 'round_globally',
                'account_journal_early_pay_discount_loss_account_id': 'chart_682',
                'account_journal_early_pay_discount_gain_account_id': 'chart_728',
                'account_sale_tax_id': 'iva_pt_sale_normal',
                'account_purchase_tax_id': 'iva_pt_purchase_normal',
                'income_account_id': 'chart_711',
                'expense_account_id': 'chart_311',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'chart_331',
            },
        }

    @template(model='account.journal')
    def _get_account_journal(self, template_code):
        vals = super()._get_account_journal(template_code)
        if template_code == 'pt':
            if 'cash' in vals:
                vals['cash']['default_account_id'] = 'chart_11'
            if 'bank' in vals:
                vals['bank']['default_account_id'] = 'chart_12'
        return vals

    @template('pt', 'account.account')
    def _get_pt_account_account(self):
        return {
            'chart_331': {
                'account_stock_expense_id': 'chart_612',
                'account_stock_variation_id': 'chart_6228',
            },
        }
