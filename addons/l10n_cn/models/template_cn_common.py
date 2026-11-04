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
            'property_account_receivable_id': 'l10n_cn_common_account_1122',
            'property_account_payable_id': 'l10n_cn_common_account_2202',
            'property_stock_valuation_account_id': 'l10n_cn_common_account_1405',
            'property_stock_account_production_cost_id': 'l10n_cn_common_account_1411',
        }

    @template('cn_common', 'res.company')
    def _get_cn_common_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cn',
                'bank_account_code_prefix': '1002',
                'cash_account_code_prefix': '1001',
                'deferred_expense_account_id': 'l10n_cn_common_account_1801',
                'deferred_revenue_account_id': 'l10n_cn_common_account_2401',
                'account_default_pos_receivable_account_id': 'l10n_cn_common_account_112201',
            },
        }

    @template('cn_common', 'account.journal')
    def _get_cn_account_journal(self):
        return {
            'cash': {'default_account_id': 'l10n_cn_common_account_1001'},
            'bank': {'default_account_id': 'l10n_cn_common_account_1002'},
        }
