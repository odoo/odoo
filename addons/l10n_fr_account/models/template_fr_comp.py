from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('fr_comp')
    def _get_fr_comp_template_data(self):
        return {
            'name': self.env._("Companies accounting plan"),
            'parent': 'fr',
            'sequence': 0,
            'code_digits': 6,
            'property_account_receivable_id': 'fr_pcg_recv',
            'property_account_payable_id': 'fr_pcg_pay',
            'property_account_downpayment_categ_id': 'pcg_4191',
        }

    @template('fr_comp', 'res.company')
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
                'l10n_fr_rounding_difference_loss_account_id': 'pcg_4768',
                'l10n_fr_rounding_difference_profit_account_id': 'pcg_4778',
                'account_sale_tax_id': 'tva_normale',
                'account_purchase_tax_id': 'tva_acq_normale',
                'expense_account_id': 'pcg_607_account',
                'income_account_id': 'pcg_707_account',
                'downpayment_account_id': 'pcg_4191',
                'account_stock_valuation_id': 'pcg_31_account',
            },
        }
