# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cn_large_bis')
    def _get_cn_large_bis_template_data(self):
        return {
            'name': _('Accounting Standards for Business Enterprises'),
            'parent': 'cn_common',
            'property_account_expense_categ_id': 'l10n_cn_large_bis_account_6401',
            'property_account_income_categ_id': 'l10n_cn_large_bis_account_6001',
        }

    @template('cn_large_bis', 'res.company')
    def _get_cn_large_bis_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cn',
                'transfer_account_code_prefix': '1004',
                'income_currency_exchange_account_id': 'l10n_cn_large_bis_account_6061',
                'expense_currency_exchange_account_id': 'l10n_cn_large_bis_account_6061',
                'account_journal_suspense_account_id': 'l10n_cn_large_bis_account_100201',
                'transfer_account_id': 'l10n_cn_large_bis_account_1004',
                'account_production_wip_account_id': 'l10n_cn_large_bis_account_140501',
                'default_cash_difference_income_account_id': 'l10n_cn_large_bis_account_630101',
                'default_cash_difference_expense_account_id': 'l10n_cn_large_bis_account_671101',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_cn_large_bis_account_630102',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_cn_large_bis_account_671102',
                'account_production_wip_overhead_account_id': 'l10n_cn_large_bis_account_140502',
                'account_sale_tax_id': 'l10n_cn_tax_large_bis_sales_excluded_13',
                'account_purchase_tax_id': 'l10n_cn_purchase_excluded_13',
                'expense_account_id': 'l10n_cn_large_bis_account_6401',
                'income_account_id': 'l10n_cn_large_bis_account_6001',
            },
        }
