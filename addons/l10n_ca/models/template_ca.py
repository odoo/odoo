# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ca_2023')
    def _get_ca_template_data(self):
        return {
            'code_digits': '0',
        }

    @template('ca_2023', 'res.company')
    def _get_ca_res_company(self):

        default_sales_tax, default_purchase_tax = {
            'BC': ('gstpst_sale_tax_12_bc', 'gstpst_purchase_tax_12_bc'),
            'MB': ('gstpst_sale_tax_12_mb', 'gstpst_purchase_tax_12_mb'),
            'QC': ('gstqst_sale_tax_14975', 'gstqst_purchase_tax_14975'),
            'SK': ('gstpst_sale_tax_11', 'gstpst_purchase_tax_11'),
            'ON': ('hst_sale_tax_13', 'hst_purchase_tax_13'),
            'NB': ('hst_sale_tax_15', 'hst_purchase_tax_15'),
            'NL': ('hst_sale_tax_15', 'hst_purchase_tax_15'),
            'NS': ('hst_sale_tax_14', 'hst_purchase_tax_14'),
            'PE': ('hst_sale_tax_15', 'hst_purchase_tax_15'),
        }.get(self.env.company.state_id.code, ('gst_sale_tax_5', 'gst_purchase_tax_5'))

        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.ca',
                'account_default_pos_receivable_account_id': 'l10n_ca_accounts_receivable_pos',
                'income_currency_exchange_account_id': 'l10n_ca_foreign_exchange_gain',
                'expense_currency_exchange_account_id': 'l10n_ca_foreign_exchange_loss',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_ca_cash_discount_loss',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_ca_cash_discount_gain',
                'account_sale_tax_id': default_sales_tax,
                'account_purchase_tax_id': default_purchase_tax,
                'income_account_id': 'l10n_ca_sales_revenue',
                'expense_account_id': 'l10n_ca_cost_of_goods_sold',
                'receivable_account_id': 'l10n_ca_accounts_receivable',
                'payable_account_id': 'l10n_ca_accounts_payable',
                'account_stock_valuation_id': 'l10n_ca_inventory_valuation',
                'default_cash_difference_income_account_id': 'l10n_ca_cash_difference_gain',
                'default_cash_difference_expense_account_id': 'l10n_ca_cash_difference_loss',
                'account_journal_suspense_account_id': 'l10n_ca_bank_suspense_account',
                'transfer_account_id': 'l10n_ca_funds_in_transfers',
                'deferred_expense_account_id': 'l10n_ca_prepaid_expenses',
                'deferred_revenue_account_id': 'l10n_ca_deferred_revenue',
                'account_production_wip_account_id': 'l10n_ca_work_in_progress',
                'downpayment_account_id': 'l10n_ca_customer_deposits',
            },
        }

    @template('ca_2023', 'account.journal')
    def _get_ca_account_journal(self):
        return {
            'bank': {
                'default_account_id': 'l10n_ca_bank',
            },
        }

    @template('ca_2023', 'account.account')
    def _get_ca_account_account(self):
        return {
            'l10n_ca_inventory_valuation': {
                'account_stock_variation_id': 'l10n_ca_inventory_variation',
            },
        }

    @template('ca_2023', 'account.fiscal.position')
    def _get_ca_account_fiscal_position(self):
        """ Ensure the appropriate domestic_fiscal_position_id gets set. """
        code = (self.env.company.state_id.code or '').lower()
        if code in ('ab', 'bc', 'mb', 'nb', 'nl', 'ns', 'nt', 'nu', 'on', 'pe', 'qc', 'sk', 'yt'):
            return {f'fiscal_position_template_{code}': {'sequence': 1}}
        return {}

    def _get_accounts_data_values(self, company, template_data, bank_prefix='', code_digits=0):
        accounts_data = super()._get_accounts_data_values(company, template_data, bank_prefix=bank_prefix, code_digits=code_digits)
        if company.account_fiscal_country_id.code == 'CA':
            accounts_data['default_cash_difference_expense_account_id'].update({
                'description': self.env._('Losses resulting from discrepancies in cash balances or reconciliations'),
            })
        return accounts_data
