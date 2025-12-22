# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('uy')
    def _get_uy_template_data(self):
        return {
            'property_account_receivable_id': 'uy_code_11300',
            'property_account_payable_id': 'uy_code_21100',
            'property_account_income_categ_id': 'uy_code_4102',
            'property_account_expense_categ_id': 'uy_code_5100',
            'code_digits': '6',
            'name': _('Uruguayan Generic Chart of Accounts'),
        }

    @template('uy', 'res.company')
    def _get_uy_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.uy',
                'bank_account_code_prefix': '1111',
                'cash_account_code_prefix': '1112',
                'transfer_account_code_prefix': '11120',
                'account_default_pos_receivable_account_id': 'uy_code_11307',
                'income_currency_exchange_account_id': 'uy_code_4302',
                'expense_currency_exchange_account_id': 'uy_code_5302',
                'account_journal_early_pay_discount_loss_account_id': 'uy_code_5303',
                'account_journal_early_pay_discount_gain_account_id': 'uy_code_4303',
                'account_sale_tax_id': 'vat1',
                'account_purchase_tax_id': 'vat4',
                'deferred_expense_account_id': 'uy_code_11407',
                'deferred_revenue_account_id': 'uy_code_21321',
            },
        }

    @template('uy', 'account.journal')
    def _get_uy_account_journal(self):
        return {
            'sale': {
                "name": _("Customer Invoices"),
                "code": "0001",
                "l10n_latam_use_documents": True,
                "refund_sequence": False,
            },
            'purchase': {
                "name": _("Vendor Bills"),
                "code": "0002",
                "l10n_latam_use_documents": True,
                "refund_sequence": False,
            },
        }

    def _load(self, template_code, company, install_demo, force_create=True):
        """ Set companies rut as the company identification type  after install the chart of account,
        this one is the uruguayan vat """
        res = super()._load(template_code, company, install_demo, force_create)
        if template_code == 'uy':
            company.partner_id.l10n_latam_identification_type_id = self.env.ref('l10n_uy.it_rut')
        return res
