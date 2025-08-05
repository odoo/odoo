# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('nz')
    def _get_nz_template_data(self):
        return {
            'code_digits': '5',
            'property_account_receivable_id': 'nz_11200',
            'property_account_payable_id': 'nz_21200',
            'property_stock_valuation_account_id': 'nz_11330',
            'property_stock_account_production_cost_id': 'nz_11350',
        }

    @template('nz', 'res.company')
    def _get_nz_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.nz',
                'bank_account_code_prefix': '1111',
                'cash_account_code_prefix': '1113',
                'transfer_account_code_prefix': '11170',
                'account_default_pos_receivable_account_id': 'nz_11220',
                'income_currency_exchange_account_id': 'nz_61630',
                'expense_currency_exchange_account_id': 'nz_61630',
                'account_journal_early_pay_discount_loss_account_id': 'nz_61610',
                'account_journal_early_pay_discount_gain_account_id': 'nz_61620',
                'account_sale_tax_id': 'nz_tax_sale_15',
                'account_purchase_tax_id': 'nz_tax_purchase_15',
                'fiscalyear_last_month': '3',
                'fiscalyear_last_day': 31,
                'expense_account_id': 'nz_51110',
                'income_account_id': 'nz_41110',
            },
        }
