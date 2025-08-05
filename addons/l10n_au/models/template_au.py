# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('au')
    def _get_au_template_data(self):
        return {
            'code_digits': '5',
            'property_account_receivable_id': 'au_11200',
            'property_stock_account_production_cost_id': 'au_11350',
            'property_account_payable_id': 'au_21200',
            'property_stock_valuation_account_id': 'au_11330',
        }

    @template('au', 'res.company')
    def _get_au_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
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
                'account_sale_tax_id': 'au_tax_sale_10',
                'account_purchase_tax_id': 'au_tax_purchase_10_service',
                'income_account_id': 'au_41110',
                'expense_account_id': 'au_51110',
            },
        }
