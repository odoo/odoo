# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('fr_pca')
    def _get_fr_pca_template_data(self):
        return {
            'name': _('Plan comptable associatif'),
            'code_digits': 6,
            'property_account_receivable_id': 'fr_pca_pcg_recv',
            'property_account_payable_id': 'fr_pca_pcg_pay',
            'property_account_expense_categ_id': 'pca_6071',
            'property_account_income_categ_id': 'pca_7071',
            'property_account_downpayment_categ_id': 'pca_4191',
        }

    @template('fr_pca', 'res.company')
    def _get_fr_pca_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.fr',
                'bank_account_code_prefix': '512',
                'cash_account_code_prefix': '53',
                'transfer_account_code_prefix': '58',
                'account_default_pos_receivable_account_id': 'fr_pca_pcg_recv_pos',
                'income_currency_exchange_account_id': 'pca_766',
                'expense_currency_exchange_account_id': 'pca_666',
                'account_journal_suspense_account_id': 'pca_471',
                'account_journal_early_pay_discount_loss_account_id': 'pca_665',
                'account_journal_early_pay_discount_gain_account_id': 'pca_765',
                'deferred_expense_account_id': 'pca_486',
                'deferred_revenue_account_id': 'pca_487',
                'l10n_fr_rounding_difference_loss_account_id': 'pca_658',
                'l10n_fr_rounding_difference_profit_account_id': 'pca_758',
                'account_sale_tax_id': 'tva_normale',
                'account_purchase_tax_id': 'tva_acq_normale',
            },
        }

    @template('fr_pca', 'account.journal')
    def _get_fr_pca_account_journal(self):
        return {
            'sale': {'refund_sequence': True},
            'purchase': {'refund_sequence': True},
        }

    @template('fr_pca', 'account.reconcile.model')
    def _get_fr_pca_reconcile_model(self):
        return {
            'bank_charges_reconcile_model': {
                'name': 'Bank fees',
                'line_ids': [
                    Command.create({
                        'account_id': 'pca_6278',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                    }),
                ],
            },
        }
