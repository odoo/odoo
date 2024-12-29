from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('fr_asso')
    def _get_fr_asso_template_data(self):
        return {
            'name': self.env._("Associations accounting plan"),
            'parent': 'fr',
            'code_digits': 6,
            'property_account_expense_categ_id': 'pca_6071',
            'property_account_income_categ_id': 'pca_7071',
            'property_account_receivable_id': 'pcg_411_account',
            'property_account_payable_id': 'pcg_401_account',
            'downpayment_account_id': 'pcg_4191',
        }

    @template('fr_asso', 'res.company')
    def _get_fr_asso_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.fr',
                'bank_account_code_prefix': '512',
                'cash_account_code_prefix': '53',
                'transfer_account_code_prefix': '58',
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
                'downpayment_account_id': 'pcg_4191',
                'account_stock_valuation_id': 'pcg_31_account',
            },
        }
