# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cn')
    def _get_cn_template_data(self):
        return {
            'parent': 'cn_common',
        }

    @template('cn', 'res.company')
    def _get_cn_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cn',
                'bank_account_code_prefix': '1002',
                'cash_account_code_prefix': '1001',
                'transfer_account_code_prefix': '1012',
                'account_default_pos_receivable_account_id': 'l10n_cn_common_112400',
                'income_currency_exchange_account_id': 'l10n_cn_common_605100',
                'expense_currency_exchange_account_id': 'l10n_cn_common_671100',
                'account_sale_tax_id': 'l10n_cn_sales_included_13',
                'account_purchase_tax_id': 'l10n_cn_purchase_excluded_13',
            },
        }

    @template('cn', 'account.journal')
    def _get_cn_account_journal(self):
        return {
            'cash': {
                'name': 'Cash on Hand',
                'default_account_id': 'l10n_cn_common_100100'
            },
        }
