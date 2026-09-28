from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cr')
    def _get_cr_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('cr', 'res.company')
    def _get_cr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cr',
                'bank_account_code_prefix': '1112',
                'cash_account_code_prefix': '1111',
                'transfer_account_code_prefix': '1114',
                'receivable_account_id': 'account_account_template_112001',
                'payable_account_id': 'account_account_template_211001',
                'account_default_pos_receivable_account_id': 'account_account_template_112011',
                'income_account_id': 'account_account_template_411001',
                'expense_account_id': 'account_account_template_511001',
                'income_currency_exchange_account_id': 'account_account_template_421002',
                'expense_currency_exchange_account_id': 'account_account_template_541004',
                'account_journal_early_pay_discount_gain_account_id': 'account_account_template_421007',
                'account_journal_early_pay_discount_loss_account_id': 'account_account_template_541006',
                'default_cash_difference_income_account_id': 'account_account_template_421008',
                'default_cash_difference_expense_account_id': 'account_account_template_541007',
                'account_sale_tax_id': 'account_tax_template_iva_venta_13',
                'account_purchase_tax_id': 'account_tax_template_iva_compra_13',
                # Anexos y Estructuras v4.4: TotalImpuesto is the sum of the per-line Monto values
                'tax_calculation_rounding_method': 'round_per_line',
                'account_stock_valuation_id': 'account_account_template_113101',
                'account_production_wip_account_id': 'account_account_template_113104',
                'account_production_wip_overhead_account_id': 'account_account_template_511010',
                'deferred_expense_account_id': 'account_account_template_141004',
                'deferred_revenue_account_id': 'account_account_template_214002',
                'downpayment_account_id': 'account_account_template_211007',
                'account_cash_basis_base_account_id': 'account_account_template_911001',
            },
        }

    @template('cr', 'account.account')
    def _get_cr_account_account(self):
        return {
            'account_account_template_122001': {
                'asset_depreciation_account_id': 'account_account_template_131001',
                'asset_expense_account_id': 'account_account_template_533014',
            },
            'account_account_template_122002': {
                'asset_depreciation_account_id': 'account_account_template_131002',
                'asset_expense_account_id': 'account_account_template_533014',
            },
            'account_account_template_122301': {
                'asset_depreciation_account_id': 'account_account_template_133001',
                'asset_expense_account_id': 'account_account_template_533014',
            },
            'account_account_template_122302': {
                'asset_depreciation_account_id': 'account_account_template_133002',
                'asset_expense_account_id': 'account_account_template_533014',
            },
            'account_account_template_122303': {
                'asset_depreciation_account_id': 'account_account_template_133003',
                'asset_expense_account_id': 'account_account_template_533014',
            },
            'account_account_template_122304': {
                'asset_depreciation_account_id': 'account_account_template_133004',
                'asset_expense_account_id': 'account_account_template_533014',
            },
            'account_account_template_122305': {
                'asset_depreciation_account_id': 'account_account_template_133005',
                'asset_expense_account_id': 'account_account_template_533014',
            },
            'account_account_template_151001': {
                'asset_depreciation_account_id': 'account_account_template_151003',
                'asset_expense_account_id': 'account_account_template_533015',
            },
            'account_account_template_151002': {
                'asset_depreciation_account_id': 'account_account_template_151003',
                'asset_expense_account_id': 'account_account_template_533015',
            },
            'account_account_template_113101': {
                'account_stock_expense_id': 'account_account_template_511001',
                'account_stock_variation_id': 'account_account_template_511007',
            },
        }

    @template('cr', 'account.journal')
    def _get_cr_account_journal(self):
        return {
            'sale': {'name': 'Facturas de cliente'},
            'purchase': {'name': 'Facturas de proveedor'},
        }
