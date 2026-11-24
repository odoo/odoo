# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('bw')
    def _get_bw_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('bw', 'res.company')
    def _get_bw_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.bw',
                'bank_account_code_prefix': '1100',
                'cash_account_code_prefix': '1101',
                'transfer_account_code_prefix': '1102',
                'account_default_pos_receivable_account_id': 'bw_account_130100',
                'income_currency_exchange_account_id': 'bw_account_410000',
                'expense_currency_exchange_account_id': 'bw_account_640000',
                'default_cash_difference_income_account_id': 'bw_account_410100',
                'default_cash_difference_expense_account_id': 'bw_account_641000',
                'account_journal_early_pay_discount_loss_account_id': 'bw_account_642000',
                'account_journal_early_pay_discount_gain_account_id': 'bw_account_410200',
                'income_account_id': 'bw_account_400000',
                'expense_account_id': 'bw_account_600000',
                'receivable_account_id': 'bw_account_130000',
                'payable_account_id': 'bw_account_200000',
                'deferred_expense_account_id': 'bw_account_140000',
                'deferred_revenue_account_id': 'bw_account_200200',
                'account_stock_valuation_id': 'bw_account_120000',
                'account_production_wip_account_id': 'bw_account_120100',
                'account_production_wip_overhead_account_id': 'bw_account_120200',
                'account_bills_to_receive_id': 'bw_account_200100',
                'account_billed_not_received_id': 'bw_account_140000',
                'account_invoices_to_issue_id': 'bw_account_140100',
                'account_invoiced_not_delivered_id': 'bw_account_200200',
                'account_sale_tax_id': 'bw_tax_sale_14',
                'account_purchase_tax_id': 'bw_tax_purchase_14',
            },
        }
