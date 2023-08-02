# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cn')
    def _get_cn_template_data(self):
        return {
            'code_digits': 6,
            'use_storno_accounting': True,
            'property_account_receivable_id': 'l10n_cn_1122',
            'property_account_payable_id': 'l10n_cn_2202',
            'property_account_expense_categ_id': 'l10n_cn_6401',
            'property_account_income_categ_id': 'l10n_cn_6001',
        }

    @template('cn', 'res.company')
    def _get_cn_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cn',
                'bank_account_code_prefix': '1002',
                'cash_account_code_prefix': '1001',
                'transfer_account_code_prefix': '1012',
                'account_default_pos_receivable_account_id': 'l10n_cn_1124',
                'income_currency_exchange_account_id': 'l10n_cn_6051',
                'expense_currency_exchange_account_id': 'l10n_cn_6711',
                'account_sale_tax_id': 'l10n_cn_sales_included_13',
                'account_purchase_tax_id': 'l10n_cn_purchase_excluded_13',
            },
        }
