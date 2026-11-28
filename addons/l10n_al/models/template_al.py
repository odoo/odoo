from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('al')
    def _get_al_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('al', 'res.company')
    def _get_al_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.al',
                'bank_account_code_prefix': '512',
                'cash_account_code_prefix': '53',
                'transfer_account_code_prefix': '58',
                'income_account_id': 'l10n_al_account_705',
                'expense_account_id': 'l10n_al_account_605',
                'receivable_account_id': 'l10n_al_account_411',
                'payable_account_id': 'l10n_al_account_401',
                'income_currency_exchange_account_id': 'l10n_al_account_769',
                'expense_currency_exchange_account_id': 'l10n_al_account_669',
                'account_journal_suspense_account_id': 'l10n_al_account_471',
                'transfer_account_id': 'l10n_al_account_581',
                'account_default_pos_receivable_account_id': 'l10n_al_account_4111',
                'account_stock_valuation_id': 'l10n_al_account_351',
                'deferred_expense_account_id': 'l10n_al_account_486',
                'deferred_revenue_account_id': 'l10n_al_account_488',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_al_account_7681',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_al_account_6681',
                'default_cash_difference_income_account_id': 'l10n_al_account_758',
                'default_cash_difference_expense_account_id': 'l10n_al_account_6581',
                'account_sale_tax_id': 'l10n_al_tax_sale_20_g',
                'account_purchase_tax_id': 'l10n_al_tax_purchase_20_g',
            },
        }

    @template('al', 'account.journal')
    def _get_al_account_journal(self):
        return {
            'bank': {'default_account_id': 'l10n_al_account_5121'},
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        # Accounts created from a code prefix (bank, cash, transfer, outstanding) go under their class.
        if template_code == 'al' and code_prefix:
            return f'l10n_al_account_{code_prefix[0]}'
        return super()._get_account_parent_xmlid(code_prefix, template_code)
