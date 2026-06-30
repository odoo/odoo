# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mx')
    def _get_mx_template_data(self):
        return {
            'code_digits': '3',
            'display_invoice_amount_total_words': True,
            'property_account_receivable_id': 'cuenta105_01',
            'property_account_payable_id': 'cuenta201_01',
            'property_account_expense_categ_id': 'cuenta601_84',
            'property_account_income_categ_id': 'cuenta401_01',
            'property_stock_account_input_categ_id': 'cuenta205_06_01',
            'property_stock_account_output_categ_id': 'cuenta107_05_01',
            'property_stock_valuation_account_id': 'cuenta115_01',
            'property_cash_basis_base_account_id': 'cuenta801_01_99',
        }

    @template('mx', 'res.company')
    def _get_mx_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.mx',
                'bank_account_code_prefix': '102.01.0',
                'cash_account_code_prefix': '101.01.0',
                'transfer_account_code_prefix': '102.01.01',
                'account_default_pos_receivable_account_id': 'cuenta105_02',
                'income_currency_exchange_account_id': 'cuenta702_01',
                'expense_currency_exchange_account_id': 'cuenta701_01',
                'deferred_expense_account_id': 'cuenta173_01',
                'account_journal_early_pay_discount_loss_account_id': 'cuenta402_01',
                'account_journal_early_pay_discount_gain_account_id': 'cuenta503_01',
                'tax_cash_basis_journal_id': 'cbmx',
                'account_sale_tax_id': 'tax12',
                'account_purchase_tax_id': 'tax14',
            },
        }

    @template('mx', 'account.journal')
    def _get_mx_account_journal(self):
        return {
            "cbmx": {
                'type': 'general',
                'name': _('Effectively Paid'),
                'code': 'CBMX',
                'default_account_id': "cuenta118_01",
                'show_on_dashboard': True,
            }
        }
        
    def _get_accounts_data_values(self, company, template_data):
        accounts_data = super()._get_accounts_data_values(company, template_data)
        if company.account_fiscal_country_id.code == 'MX':
            accounts_data.update({
                'default_cash_difference_income_account_id' : {
                    'name': _('Other Income'),
                    'code': '403.01.01'
                },
                'default_cash_difference_expense_account_id': {
                    'name': 'Cash Difference Loss',
                    'code': '601.84.02',
                }
            })
        return accounts_data
