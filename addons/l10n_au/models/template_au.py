# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('au')
    def _get_au_template_data(self):
        return {
            'code_digits': '5',
            'use_anglo_saxon': True,
            'property_account_receivable_id': 'au_11200',
            'property_stock_account_production_cost_id': 'au_11350',
            'property_account_payable_id': 'au_21200',
            'property_account_expense_categ_id': 'au_51110',
            'property_account_income_categ_id': 'au_41110',
            'property_stock_account_input_categ_id': 'au_21210',
            'property_stock_account_output_categ_id': 'au_11340',
            'property_stock_valuation_account_id': 'au_11330',
            'property_tax_payable_account_id': 'au_21320',
            'property_tax_receivable_account_id': 'au_21320',
        }

    @template('au', 'res.company')
    def _get_au_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.au',
                'bank_account_code_prefix': '1111',
                'cash_account_code_prefix': '1113',
                'transfer_account_code_prefix': '11170',
                'account_default_pos_receivable_account_id': 'au_11201',
                'income_currency_exchange_account_id': 'au_61640',
                'expense_currency_exchange_account_id': 'au_61630',
                'account_journal_early_pay_discount_loss_account_id': 'au_61610',
                'account_journal_early_pay_discount_gain_account_id': 'au_61620',
                'fiscalyear_last_month': '6',
                'fiscalyear_last_day': 30,
                # Changing the opening date to the first day of the fiscal year.
                # This way the opening entries will be set to the 30th of June.
                'account_opening_date': fields.Date.context_today(self).replace(month=7, day=1),
                'account_sale_tax_id': 'au_tax_sale_10',
                'account_purchase_tax_id': 'au_tax_purchase_10_service',
            },
        }
