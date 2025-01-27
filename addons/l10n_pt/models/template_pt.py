# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pt')
    def _get_pt_template_data(self):
        return {
            'property_account_receivable_id': 'chart_2111',
            'property_account_payable_id': 'chart_2211',
        }

    @template('pt', 'res.company')
    def _get_pt_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pt',
                'bank_account_code_prefix': '12',
                'cash_account_code_prefix': '11',
                'transfer_account_code_prefix': '1431',
                'account_default_pos_receivable_account_id': 'chart_2117',
                'income_currency_exchange_account_id': 'chart_7861',
                'expense_currency_exchange_account_id': 'chart_6863',
                'account_journal_early_pay_discount_loss_account_id': 'chart_682',
                'account_journal_early_pay_discount_gain_account_id': 'chart_728',
                'tax_calculation_rounding_method': 'round_globally',
                'account_sale_tax_id': 'iva_pt_sale_normal',
                'account_purchase_tax_id': 'iva_pt_purchase_normal',
                'income_account_id': 'chart_711',
                'expense_account_id': 'chart_311',
            },
        }

    @template('pt', 'account.journal')
    def _get_pt_account_account_journal(self):
        return {
            'sale': {
                'refund_sequence': True,
            },
        }

    def _load(self, template_code, company, install_demo):
        """
        Set tax calculation rounding method required in the Portuguese localization to
        prevent rounding errors according to the requirements of the Autoridade Tributaria
        """
        res = super()._load(template_code, company, install_demo)
        if company.account_fiscal_country_id.code == 'PT':
            company.write({'tax_calculation_rounding_method': 'round_globally'})
        return res
