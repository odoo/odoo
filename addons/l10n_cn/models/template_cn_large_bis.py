# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cn_large_bis')
    def _get_cn_large_bis_template_data(self):
        return {
            'name': _('Large Business'),
            'parent': 'cn_common',
        }

    @template('cn_large_bis', 'res.company')
    def _get_cn_large_bis_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cn',
                'bank_account_code_prefix': '1002',
                'cash_account_code_prefix': '1001',
                'transfer_account_code_prefix': '1012',
                'account_default_pos_receivable_account_id': 'l10n_cn_common_112400',
                'income_currency_exchange_account_id': 'l10n_cn_common_605100',
                'expense_currency_exchange_account_id': 'l10n_cn_common_671100',
                'account_sale_tax_id': 'l10n_cn_tax_large_bis_sales_included_13',
                'account_purchase_tax_id': 'l10n_cn_tax_large_bis_purchase_excluded_13',
                'account_journal_suspense_account_id': 'l10n_cn_large_bis_100201',
                'account_journal_payment_debit_account_id': 'l10n_cn_large_bis_100202',
                'account_journal_payment_credit_account_id': 'l10n_cn_large_bis_100203',
                'default_cash_difference_income_account_id': 'l10n_cn_large_bis_999200',
                'default_cash_difference_expense_account_id': 'l10n_cn_large_bis_999100',
            },
        }

    @template('cn_large_bis', 'account.journal')
    def _get_cn_large_bis_account_journal(self):
        return {
            'cash': {
                'name': 'Cash on Hand',
                'default_account_id': 'l10n_cn_common_100100',
            },
            'bank': {
                'default_account_id': 'l10n_cn_large_bis_100204',
            },
        }
