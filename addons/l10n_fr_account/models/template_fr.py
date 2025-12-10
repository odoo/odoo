# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('fr')
    def _get_fr_template_data(self):
        return {
            'code_digits': 6,
            'property_account_receivable_id': 'fr_pcg_recv',
            'property_account_payable_id': 'fr_pcg_pay',
            'downpayment_account_id': 'pcg_4191',
        }

    @template('fr', 'res.company')
    def _get_fr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.fr',
                'bank_account_code_prefix': '512',
                'cash_account_code_prefix': '53',
                'transfer_account_code_prefix': '58',
                'account_default_pos_receivable_account_id': 'fr_pcg_recv_pos',
                'income_currency_exchange_account_id': 'pcg_766',
                'expense_currency_exchange_account_id': 'pcg_666',
                'account_journal_suspense_account_id': 'pcg_471',
                'account_journal_early_pay_discount_loss_account_id': 'pcg_665',
                'account_journal_early_pay_discount_gain_account_id': 'pcg_765',
                'deferred_expense_account_id': 'pcg_486',
                'deferred_revenue_account_id': 'pcg_487',
                'l10n_fr_rounding_difference_loss_account_id': 'pcg_658',
                'l10n_fr_rounding_difference_profit_account_id': 'pcg_758',
                'account_sale_tax_id': 'tva_normale',
                'account_purchase_tax_id': 'tva_acq_normale',
                'expense_account_id': 'pcg_607_account',
                'income_account_id': 'pcg_707_account',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'pcg_31_account',
            },
        }

    @template('fr', 'account.journal')
    def _get_fr_account_journal(self):
        return {
            'sale': {'refund_sequence': True},
            'purchase': {'refund_sequence': True},
        }

    def _get_bank_fees_reco_account(self, company):
        # French account for the bank fees reco model. We need to be as precise
        # as possible in case it's modified so it's missing and not replaced.
        fr_account = self.env['account.account'].with_company(company).search([
            ('code', '=', '627800'),
            ('account_type', '=', 'expense'),
            ('name', '=', 'Other expenses and commissions on services supplied'),
        ], limit=1)
        return fr_account or super()._get_bank_fees_reco_account(company)

    @template('fr', 'account.account')
    def _get_fr_account_account(self):
        return {
            'pcg_31_account': {
                'account_stock_expense_id': 'pcg_601_account',
                'account_stock_variation_id': 'pcg_6031',
            },
        }
