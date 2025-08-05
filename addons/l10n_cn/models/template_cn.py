# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cn')
    def _get_cn_template_data(self):
        return {
            'name': _('Accounting Standards for Small Business Enterprises'),
            'parent': 'cn_common',
            'property_account_expense_categ_id': 'l10n_cn_account_5401',
            'property_account_income_categ_id': 'l10n_cn_account_5001',
        }

    @template('cn', 'res.company')
    def _get_cn_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cn',
                'transfer_account_code_prefix': '1012',
                'income_currency_exchange_account_id': 'l10n_cn_account_530102',
                'expense_currency_exchange_account_id': 'l10n_cn_account_560302',
                'account_journal_suspense_account_id': 'l10n_cn_account_101201',
                'transfer_account_id': 'l10n_cn_account_101202',
                'account_production_wip_account_id': 'l10n_cn_account_1406',
                'default_cash_difference_income_account_id': 'l10n_cn_account_530103',
                'default_cash_difference_expense_account_id': 'l10n_cn_account_560303',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_cn_account_530104',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_cn_account_560304',
                'account_production_wip_overhead_account_id': 'l10n_cn_account_140601',
                'account_sale_tax_id': 'l10n_cn_sales_excluded_13',
                'account_purchase_tax_id': 'l10n_cn_purchase_excluded_13',
                'expense_account_id': 'l10n_cn_account_5401',
                'income_account_id': 'l10n_cn_account_5001',
            },
        }
