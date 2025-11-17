# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ar_base')
    def _get_ar_base_template_data(self):
        return {
            'property_account_receivable_id': 'base_deudores_por_ventas',
            'property_account_payable_id': 'base_proveedores',
            'name': _('Generic Chart of Accounts Argentina Single Taxpayer / Basis'),
            'code_digits': '12',
            'sequence': 1,
        }

    @template('ar_base', 'res.company')
    def _get_ar_base_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ar',
                'bank_account_code_prefix': '1.1.1.02.',
                'cash_account_code_prefix': '1.1.1.01.',
                'transfer_account_code_prefix': '6.0.00.00.',
                'account_default_pos_receivable_account_id': 'base_deudores_por_ventas_pos',
                'income_currency_exchange_account_id': 'base_diferencias_de_cambio',
                'expense_currency_exchange_account_id': 'base_diferencias_de_cambio',
                'expense_account_id': 'base_compra_mercaderia',
                'income_account_id': 'base_venta_de_mercaderia',
                'display_invoice_tax_company_currency': False,
                'account_stock_valuation_id': 'base_mercaderia_reventa',
            },
        }

    @template('ar_base', 'account.journal')
    def _get_ar_account_journal(self):
        """ In case of an Argentinean CoA, we modify the default values of the sales journal to be a preprinted journal"""
        return {
            'sale': {
                "name": self.env._("Ventas Preimpreso"),
                "code": "0001",
                "l10n_ar_afip_pos_number": 1,
                "l10n_ar_afip_pos_partner_id": self.env.company.partner_id.id,
                "l10n_ar_afip_pos_system": 'II_IM',
                "refund_sequence": False,
            },
        }

    @template('ar_base', 'account.account')
    def _get_ar_base_account_account(self):
        return {
            'base_mercaderia_reventa': {
                'account_stock_expense_id': 'base_compra_mercaderia',
                'account_stock_variation_id': 'base_variacion_mercaderia_reventa',
            },
        }

    def _get_accounts_data_values(self, company, template_data, bank_prefix='', code_digits=0):
        accounts_data = super()._get_accounts_data_values(company, template_data, bank_prefix=bank_prefix, code_digits=code_digits)
        if company.account_fiscal_country_id.code == 'AR':
            accounts_data['default_cash_difference_expense_account_id'].update({
                'description': self.env._('Cash count differences recognized as loss.'),
            })
            accounts_data['account_journal_early_pay_discount_loss_account_id'].update({
                'description': self.env._('Discounts granted for early payment recognized as loss.'),
            })
        return accounts_data
