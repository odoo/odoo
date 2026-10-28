# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('li')
    def _get_li_template_data(self):
        return {
            'code_digits': '4',
        }

    @template('li', 'res.company')
    def _get_li_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.li',
                'bank_account_code_prefix': '102',
                'cash_account_code_prefix': '100',
                'transfer_account_code_prefix': '1090',
                'account_default_pos_receivable_account_id': 'li_coa_1101',
                'income_currency_exchange_account_id': 'li_coa_3806',
                'expense_currency_exchange_account_id': 'li_coa_4906',
                'account_journal_early_pay_discount_loss_account_id': 'li_coa_4900',
                'account_journal_early_pay_discount_gain_account_id': 'li_coa_3800',
                'default_cash_difference_expense_account_id': 'li_coa_4991',
                'default_cash_difference_income_account_id': 'li_coa_4992',
                'deferred_expense_account_id': 'li_coa_1300',
                'deferred_revenue_account_id': 'li_coa_2301',
                'account_sale_tax_id': 'li_vat_sale_81',
                'account_purchase_tax_id': 'li_vat_purchase_81',
                'external_report_layout_id': 'l10n_din5008.external_layout_din5008',
                'paperformat_id': 'l10n_din5008.paperformat_euro_din',
                'expense_account_id': 'li_coa_4200',
                'income_account_id': 'li_coa_3200',
                'receivable_account_id': 'li_coa_1100',
                'payable_account_id': 'li_coa_2000',
                'account_stock_valuation_id': 'li_coa_1210',
            },
        }

    @template('li', 'account.account')
    def _get_li_account_account(self):
        return {
            'li_coa_1210': {
                'account_stock_expense_id': 'li_coa_4000',
                'account_stock_variation_id': 'li_coa_4801',
            },
        }
