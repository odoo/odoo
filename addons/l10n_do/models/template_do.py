# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('do')
    def _get_do_template_data(self):
        return {
            'code_digits': '8',
            'property_account_receivable_id': 'do_niif_11030201',
            'property_account_payable_id': 'do_niif_21010200',
            'property_account_income_categ_id': 'do_niif_41010100',
            'property_account_expense_categ_id': 'do_niif_51010100',
            'property_stock_account_input_categ_id': 'do_niif_21021200',
            'property_stock_account_output_categ_id': 'do_niif_11050600',
            'property_stock_valuation_account_id': 'do_niif_11050100',
        }

    @template('do', 'res.company')
    def _get_do_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.do',
                'bank_account_code_prefix': '110102',
                'cash_account_code_prefix': '110101',
                'transfer_account_code_prefix': '11010100',
                'account_default_pos_receivable_account_id': 'do_niif_11030210',
                'income_currency_exchange_account_id': 'do_niif_42040100',
                'expense_currency_exchange_account_id': 'do_niif_52070800',
                'account_journal_early_pay_discount_loss_account_id': 'do_niif_99900003',
                'account_journal_early_pay_discount_gain_account_id': 'do_niif_99900004',
            },
        }

    @template('do', 'account.journal')
    def _get_do_account_journal(self):
        return {
            "caja_chica": {
                'name': _('Caja Chica'),
                'type': 'cash',
                'sequence': 10,
            },
            "cheques_clientes": {
                'name': _('Cheques Clientes'),
                'type': 'cash',
                'sequence': 10,
            },
            "gasto": {
                'type': 'purchase',
                'name': _('Gastos No Deducibles'),
                'code': 'GASTO',
                'show_on_dashboard': True,
            },
            "cxp": {
                'type': 'purchase',
                'name': _('Migración CxP'),
                'code': 'CXP',
                'show_on_dashboard': True,
            },
            "cxc": {
                'type': 'sale',
                'name': _('Migración CxC'),
                'code': 'CXC',
                'show_on_dashboard': True,
            },
        }
