# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cn_common')
    def _get_cn_common_template_data(self):
        return {
            'name': _('Common'),
            'visible': 0,
            'code_digits': 6,
            'use_storno_accounting': True,
            'property_account_receivable_id': 'l10n_cn_common_112200',
            'property_account_payable_id': 'l10n_cn_common_220200',
            'property_account_expense_categ_id': 'l10n_cn_common_640100',
            'property_account_income_categ_id': 'l10n_cn_common_600100',
        }

    @template('cn_common', 'res.company')
    def _get_cn_common_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cn',
                'bank_account_code_prefix': '1002',
                'cash_account_code_prefix': '1001',
                'transfer_account_code_prefix': '1012',
                'account_default_pos_receivable_account_id': 'l10n_cn_common_112400',
                'income_currency_exchange_account_id': 'l10n_cn_common_605100',
                'expense_currency_exchange_account_id': 'l10n_cn_common_671100',
            },
        }
