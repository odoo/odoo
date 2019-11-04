# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase


class AccountMinimalTest(SavepointCase):
    """ This should be loaded for non python tests in other modules that require
    accounting test data but that don't depend on any localization"""

    @classmethod
    def setUpClass(cls):
        super(AccountMinimalTest, cls).setUpClass()
        cls.create_accounting_minimal_data()

    @classmethod
    def create_accounting_minimal_data(cls):
        cls.company = cls.env.company
        cls.company.bank_account_code_prefix = 'X1100'

        # Chart of Accounts

        # Account Tags
        cls.demo_capital_account = cls.env['account.account.tag'].create({'name': 'Demo Capital Account'})
        cls.demo_stock_account = cls.env['account.account.tag'].create({'name': 'Demo Stock Account'})
        cls.demo_sale_of_land_account = cls.env['account.account.tag'].create({'name': 'Demo Sale of Land Account'})
        cls.demo_ceo_wages_account = cls.env['account.account.tag'].create({'name': 'Demo CEO Wages Account'})
        cls.demo_office_furniture_account = cls.env['account.account.tag'].create({'name': 'Office Furniture'})

        # Balance Sheet
        cls.xfa = cls.env['account.account'].create({
            'code': 'X1000',
            'name': 'Fixed Assets - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_fixed_assets').id,
        })
        cls.cas = cls.env['account.account'].create({
            'code': 'X1010',
            'name': 'Current Assets - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
        })
        cls.stk = cls.env['account.account'].create({
            'code': 'X1011',
            'name': 'Purchased Stocks - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'tag_ids': [(6, 0, [cls.demo_stock_account.id])]
        })
        cls.a_recv = cls.env['account.account'].create({
            'code': 'X1012',
            'name': 'Debtors - (test)',
            'reconcile': True,
            'user_type_id': cls.env.ref('account.data_account_type_receivable').id,
        })
        cls.ova = cls.env['account.account'].create({
            'code': 'X1013',
            'name': 'VAT Paid- (test)',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
        })
        cls.bnk = cls.env['account.account'].create({
            'code': 'X1014',
            'name': 'Bank Current Account - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_liquidity').id,
        })
        cls.cash = cls.env['account.account'].create({
            'code': 'X1015',
            'name': 'Cash - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_liquidity').id,
        })
        cls.o_income = cls.env['account.account'].create({
            'code': 'X1016',
            'name': 'Opening Income - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_other_income').id,
        })
        cls.usd_bnk = cls.env['account.account'].create({
            'code': 'X1017',
            'name': 'USD Bank Account - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_liquidity').id,
            'currency_id': cls.env.ref('base.USD').id,
        })
        cls.transfer_account = cls.env['account.account'].create({
            'code': 'X1019',
            'name': 'Internal Transfert Account - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        cls.ncas = cls.env['account.account'].create({
            'code': 'X1020',
            'name': 'Non-current Assets - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_non_current_assets').id,
        })
        cls.prepayements = cls.env['account.account'].create({
            'code': 'X1030',
            'name': 'Prepayments - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_prepayments').id,
        })
        cls.current_liabilities = cls.env['account.account'].create({
            'code': 'X1110',
            'name': 'Current Liabilities - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_current_liabilities').id,
        })
        cls.a_pay = cls.env['account.account'].create({
            'code': 'X1111',
            'name': 'Creditors - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_payable').id,
            'reconcile': True,
        })
        cls.iva = cls.env['account.account'].create({
            'code': 'X1112',
            'name': 'VAT Received - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_current_liabilities').id,
        })
        cls.rsa = cls.env['account.account'].create({
            'code': 'X1113',
            'name': 'Reserve and Profit/Loss - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_current_liabilities').id,
        })
        cls.cas = cls.env['account.account'].create({
            'code': 'X1120',
            'name': 'Non-current Liabilities - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_non_current_liabilities').id,
        })
        cls.o_expense = cls.env['account.account'].create({
            'code': 'X1114',
            'name': 'Opening Expense - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
        })

        # Profit and Loss
        cls.income_fx_income = cls.env['account.account'].create({
            'code': 'X2010',
            'name': 'Foreign Exchange Gain - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
            'reconcile': False,
        })
        cls.a_sale = cls.env['account.account'].create({
            'code': 'X2020',
            'name': 'Product Sales - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
            'tag_ids': [(6, 0, [cls.env.ref('account.account_tag_operating').id])],
        })
        cls.a_sale_invest = cls.env['account.account'].create({
            'code': 'X2021',
            'name': 'Sale of Lands - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
            'tag_ids': [(6, 0, [cls.env.ref('account.account_tag_investing').id])],
        })
        cls.a_sale_finance = cls.env['account.account'].create({
            'code': 'X2022',
            'name': 'Bank Accounts Interests - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
            'tag_ids': [(6, 0, [cls.env.ref('account.account_tag_financing').id])],
        })
        cls.a_sale_finance = cls.env['account.account'].create({
            'code': 'X2030',
            'name': 'Cost of Goods Sold - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_direct_costs').id,
        })
        cls.income_fx_expense = cls.env['account.account'].create({
            'code': 'X2110',
            'name': 'Foreign Exchange Loss - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
            'reconcile': False,
        })
        cls.a_expense = cls.env['account.account'].create({
            'code': 'X2120',
            'name': 'Expenses - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
            'tag_ids': [(6, 0, [cls.env.ref('account.account_tag_operating').id])],
        })
        cls.a_salary_expense = cls.env['account.account'].create({
            'code': 'X2121',
            'name': 'Salary Expenses - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
            'tag_ids': [(6, 0, [cls.env.ref('account.account_tag_operating').id])],
        })
        cls.a_expense_invest = cls.env['account.account'].create({
            'code': 'X2122',
            'name': 'Purchase of Equipments - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_fixed_assets').id,
            'tag_ids': [(6, 0, [cls.env.ref('account.account_tag_investing').id])],
        })
        cls.a_expense_finance = cls.env['account.account'].create({
            'code': 'X2123',
            'name': 'Bank Fees - (test)',
            'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
            'tag_ids': [(6, 0, [cls.env.ref('account.account_tag_financing').id])],
        })
        cls.a_capital = cls.env['account.account'].create({
            'code': 'X3001',
            'name': 'Capital',
            'user_type_id': cls.env.ref('account.data_account_type_equity').id,
        })
        cls.a_dividends = cls.env['account.account'].create({
            'code': 'X3002',
            'name': 'Dividends',
            'user_type_id': cls.env.ref('account.data_account_type_equity').id,
        })

        # Properties: Product income and expense accounts, default parameters
        cls.env['ir.property'].create([{
            'name': 'property_account_receivable_id',
            'fields_id': cls.env['ir.model.fields'].search([('model', '=', 'res.partner'), ('name', '=', 'property_account_receivable_id')], limit=1).id,
            'value': 'account.account,%s' % (cls.a_recv.id),
            'company_id': cls.company.id,
        }, {
            'name': 'property_account_payable_id',
            'fields_id': cls.env['ir.model.fields'].search([('model', '=', 'res.partner'), ('name', '=', 'property_account_payable_id')], limit=1).id,
            'value': 'account.account,%s' % (cls.a_pay.id),
            'company_id': cls.company.id,
        }, {
            'name': 'property_account_position_id',
            'fields_id': cls.env['ir.model.fields'].search([('model', '=', 'res.partner'), ('name', '=', 'property_account_position_id')], limit=1).id,
            'value': False,
            'company_id': cls.company.id,
        }, {
            'name': 'property_account_expense_categ_id',
            'fields_id': cls.env['ir.model.fields'].search([('model', '=', 'product.category'), ('name', '=', 'property_account_expense_categ_id')], limit=1).id,
            'value': 'account.account,%s' % (cls.a_expense.id),
            'company_id': cls.company.id,
        }, {
            'name': 'property_account_income_categ_id',
            'fields_id': cls.env['ir.model.fields'].search([('model', '=', 'product.category'), ('name', '=', 'property_account_income_categ_id')], limit=1).id,
            'value': 'account.account,%s' % (cls.a_sale.id),
            'company_id': cls.company.id,
        }])

        # Bank Accounts
        cls.bank_account = cls.env['res.partner.bank'].create({
            'acc_number': '987654321',
            'bank_name': 'Bank',
            'partner_id': cls.company.partner_id.id,
        })
        cls.bank_account_usd = cls.env['res.partner.bank'].create({
            'acc_number': '123456789',
            'bank_name': 'Bank US',
            'partner_id': cls.company.partner_id.id,
        })

        # Account Journal
        cls.sales_journal = cls.env['account.journal'].create({
            'name': 'Customer Invoices - Test',
            'code': 'TINV',
            'type': 'sale',
            'default_credit_account_id': cls.a_sale.id,
            'default_debit_account_id': cls.a_sale.id,
            'refund_sequence': True,
        })
        cls.expenses_journal = cls.env['account.journal'].create({
            'name': 'Vendor Bills - Test',
            'code': 'TEXJ',
            'type': 'purchase',
            'default_credit_account_id': cls.a_expense.id,
            'default_debit_account_id': cls.a_expense.id,
            'refund_sequence': True,
        })
        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Bank - Test',
            'code': 'TBNK',
            'type': 'bank',
            'default_credit_account_id': cls.bnk.id,
            'default_debit_account_id': cls.bnk.id,
        })
        cls.cash_journal = cls.env['account.journal'].create({
            'name': 'Cash - Test',
            'code': 'TCSH',
            'type': 'cash',
            'profit_account_id': cls.rsa.id,
            'loss_account_id': cls.rsa.id,
            'default_credit_account_id': cls.cash.id,
            'default_debit_account_id': cls.cash.id,
        })
        cls.miscellaneous_journal = cls.env['account.journal'].create({
            'name': 'Miscellaneous - Test',
            'code': 'TMIS',
            'type': 'general',
            'show_on_dashboard': False,
        })
        cls.currency_diff_journal = cls.env['account.journal'].create({
            'name': 'Currency Difference - Test',
            'code': 'CUR',
            'type': 'general',
            'default_credit_account_id': cls.income_fx_expense.id,
            'default_debit_account_id': cls.income_fx_income.id,
            'show_on_dashboard': False,
        })
        cls.bank_journal_usd = cls.env['account.journal'].create({
            'name': 'USD Bank - Test',
            'code': 'TUBK',
            'type': 'bank',
            'default_credit_account_id': cls.usd_bnk.id,
            'default_debit_account_id': cls.usd_bnk.id,
            'bank_account_id': cls.bank_account_usd.id,
        })

        cls.company.currency_exchange_journal_id = cls.currency_diff_journal.id
