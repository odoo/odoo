from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('generic_coa')
    def _get_generic_coa_template_data(self):
        """Return the data necessary for the chart template.

        :return: all the values that are not stored but are used to instancieate
                 the chart of accounts. Common keys are:
                 * property_*
                 * code_digits
        :rtype: dict
        """
        return {
            'name': _("Generic Chart of Accounts"),
            'country': None,
            'property_account_receivable_id': 'receivable',
            'property_account_payable_id': 'payable',
        }

    @template('generic_coa', 'res.company')
    def _get_generic_coa_res_company(self):
        """Return the data to be written on the company.

        The data is a mapping the XMLID to the create/write values of a record.

        :rtype: dict[(str, int), dict]
        """
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.us',
                'bank_account_code_prefix': '1014',
                'cash_account_code_prefix': '1015',
                'transfer_account_code_prefix': '1017',
                'account_default_pos_receivable_account_id': 'pos_receivable',
                'income_currency_exchange_account_id': 'income_currency_exchange',
                'expense_currency_exchange_account_id': 'expense_currency_exchange',
                'default_cash_difference_income_account_id': 'cash_diff_income',
                'default_cash_difference_expense_account_id': 'cash_diff_expense',
                'account_journal_early_pay_discount_loss_account_id': 'cash_discount_loss',
                'account_journal_early_pay_discount_gain_account_id': 'cash_discount_gain',
                'expense_account_id': 'expense',
                'income_account_id': 'income',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'stock_valuation',
                'account_production_wip_account_id': 'wip',
                'account_production_wip_overhead_account_id': 'cost_of_production',
            },
        }

    @template('generic_coa', 'account.account')
    def _get_generic_coa_account_account(self):
        return {
            'stock_valuation': {
                'account_stock_variation_id': 'stock_variation',
            },
        }
