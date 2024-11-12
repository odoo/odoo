# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('dk')
    def _get_dk_template_data(self):
        return {
            'property_account_receivable_id': 'dk_coa_6190',
            'property_account_payable_id': 'dk_coa_7440',
            'property_account_expense_categ_id': 'dk_coa_1610',
            'property_account_income_categ_id': 'dk_coa_1010',
            'code_digits': '4',
        }

    @template('dk', 'res.company')
    def _get_dk_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.dk',
                'bank_account_code_prefix': '648',
                'cash_account_code_prefix': '647',
                'transfer_account_code_prefix': '683',
                'account_default_pos_receivable_account_id': 'dk_coa_6190',
                'income_currency_exchange_account_id': 'dk_coa_3610',
                'expense_currency_exchange_account_id': 'dk_coa_3610',
                'account_journal_early_pay_discount_loss_account_id': 'dk_coa_2720',
                'account_journal_early_pay_discount_gain_account_id': 'dk_coa_2720',
                'account_sale_tax_id': 'tax_s1',
                'account_purchase_tax_id': 'tax_k1',
            },
        }

    def _setup_utility_bank_accounts(self, template_code, company, template_data):
        super()._setup_utility_bank_accounts(template_code, company, template_data)
        if template_code == 'dk':
            company.account_journal_suspense_account_id.tag_ids = self.env.ref('l10n_dk.account_tag_6482')
            company.transfer_account_id.tag_ids = self.env.ref('l10n_dk.account_tag_6831')
