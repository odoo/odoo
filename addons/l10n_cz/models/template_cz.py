# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cz')
    def _get_cz_template_data(self):
        return {
            'code_digits': '6',
            'use_storno_accounting': True,
            'property_account_receivable_id': 'chart_cz_311000',
            'property_account_payable_id': 'chart_cz_321000',
            'property_stock_valuation_account_id': 'chart_cz_132000',
        }

    @template('cz', 'res.company')
    def _get_cz_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cz',
                'bank_account_code_prefix': '221',
                'cash_account_code_prefix': '211',
                'transfer_account_code_prefix': '261',
                'income_currency_exchange_account_id': 'chart_cz_663000',
                'expense_currency_exchange_account_id': 'chart_cz_563000',
                'account_journal_suspense_account_id': 'chart_cz_261000',
                'default_cash_difference_income_account_id': 'chart_cz_668000',
                'default_cash_difference_expense_account_id': 'chart_cz_568000',
                'account_default_pos_receivable_account_id': 'chart_cz_311001',
                'account_sale_tax_id': 'l10n_cz_21_domestic_supplies',
                'account_purchase_tax_id': 'l10n_cz_21_receipt_domestic_supplies',
                'expense_account_id': 'chart_cz_504000',
                'income_account_id': 'chart_cz_604000',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'chart_cz_131000',
            },
        }

    @api.model
    def _get_demo_data_move(self, company=False):
        data = super()._get_demo_data_move(company)
        if company and company.account_fiscal_country_id.code == 'CZ':
            for key in (
                'demo_invoice_1',
                'demo_invoice_2',
                'demo_invoice_3',
                'demo_invoice_followup',
                'demo_invoice_5',
                'demo_invoice_6',
                'demo_invoice_7',
                'demo_invoice_8',
                'demo_invoice_equipment_purchase',
                'demo_invoice_9',
                'demo_invoice_10',
                'demo_move_auto_reconcile_1',
                'demo_move_auto_reconcile_2',
                'demo_move_auto_reconcile_3',
                'demo_move_auto_reconcile_4',
                'demo_move_auto_reconcile_5',
                'demo_move_auto_reconcile_6',
                'demo_move_auto_reconcile_7',
            ):
                vals = data[self.company_xmlid(key)]
                if invoice_date := vals.get('invoice_date'):
                    vals['taxable_supply_date'] = invoice_date
        return data

    @template('cz', 'account.account')
    def _get_cz_account_account(self):
        return {
            'chart_cz_131000': {
                'account_stock_expense_id': 'chart_cz_504000',
                'account_stock_variation_id': 'chart_cz_583000',
            },
        }
