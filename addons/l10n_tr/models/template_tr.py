# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('tr')
    def _get_tr_template_data(self):
        return {
            'property_account_receivable_id': 'tr120',
            'property_account_payable_id': 'tr320',
            'code_digits': '6',
        }

    @template('tr', 'res.company')
    def _get_tr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.tr',
                'bank_account_code_prefix': '102',
                'cash_account_code_prefix': '100',
                'transfer_account_code_prefix': '103',
                'account_default_pos_receivable_account_id': 'tr123',
                'income_currency_exchange_account_id': 'tr646',
                'expense_currency_exchange_account_id': 'tr656',
                'account_journal_suspense_account_id': 'tr102999',
                'account_sale_tax_id': 'tr_s_20',
                'account_purchase_tax_id': 'tr_p_20',
                'deferred_expense_account_id': 'tr180',
                'deferred_revenue_account_id': 'tr380',
                'expense_account_id': 'tr150',
                'income_account_id': 'tr600',
                'tax_calculation_rounding_method': 'round_per_line',
            },
        }

    @template('tr', 'account.journal')
    def _get_tr_account_journal(self):
        return {
            'cash': {
                'name': _("Cash"),
                'type': 'cash',
                'show_on_dashboard': True,
            },
        }
