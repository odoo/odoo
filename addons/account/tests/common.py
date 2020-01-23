# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import time

from odoo import fields
from odoo.addons.base.tests.common import SavepointCaseWithUserDemo
from odoo.exceptions import ValidationError
from odoo.tests.common import SavepointCase, HttpCase, tagged, Form

import logging

_logger = logging.getLogger(__name__)


class AccountTestCommon(SavepointCase):
    """ This should be loaded for non python tests in other modules that require
    accounting test data but that don't depend on any localization"""

    @classmethod
    def setUpClass(cls):
        super(AccountTestCommon, cls).setUpClass()
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
        cls.sus = cls.env['account.account'].create({
            'name': 'Suspense Account - (test)',
            'code': 'X1115',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
        })
        cls.company.account_journal_suspense_account_id = cls.sus

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
        Property = cls.env['ir.property']
        Property.set_default('property_account_receivable_id', 'res.partner', cls.a_recv, cls.company)
        Property.set_default('property_account_payable_id', 'res.partner', cls.a_pay, cls.company)
        Property.set_default('property_account_position_id', 'res.partner', False, cls.company)
        Property.set_default('property_account_expense_categ_id', 'product.category', cls.a_expense, cls.company)
        Property.set_default('property_account_income_categ_id', 'product.category', cls.a_sale, cls.company)

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
            'refund_sequence': True,
        })
        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Bank - Test',
            'code': 'TBNK',
            'type': 'bank',
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


class AccountTestUsersCommon(AccountTestCommon):

    """Tests for diffrent type of user 'Accountant/Adviser' and added groups"""

    @classmethod
    def setUpClass(cls):
        super(AccountTestUsersCommon, cls).setUpClass()
        cls.res_user_model = cls.env['res.users']
        cls.main_company = cls.env.ref('base.main_company')
        cls.main_partner = cls.env.ref('base.main_partner')
        cls.main_bank = cls.env.ref('base.res_bank_1')
        res_users_account_user = cls.env.ref('account.group_account_invoice')
        res_users_account_manager = cls.env.ref('account.group_account_manager')
        partner_manager = cls.env.ref('base.group_partner_manager')
        cls.tax_model = cls.env['account.tax']
        cls.account_model = cls.env['account.account']
        cls.account_type_model = cls.env['account.account.type']
        cls.currency_euro = cls.env.ref('base.EUR')

        cls.account_user = cls.res_user_model.with_context({'no_reset_password': True}).create(dict(
            name="Accountant",
            company_id=cls.main_company.id,
            login="acc",
            email="accountuser@yourcompany.com",
            groups_id=[(6, 0, [res_users_account_user.id, partner_manager.id])]
        ))
        cls.account_manager = cls.res_user_model.with_context({'no_reset_password': True}).create(dict(
            name="Adviser",
            company_id=cls.main_company.id,
            login="fm",
            email="accountmanager@yourcompany.com",
            groups_id=[(6, 0, [res_users_account_manager.id, partner_manager.id])]
        ))


class AccountTestNoChartCommon(SavepointCaseWithUserDemo):
    """ Some tests required to be executed at module installation, and not 'post install', like moslty
        of accounting tests, since a chart of account is required
        This test setup class provides data for test suite to make business flow working without a chart
        of account installed. The class provide some helpers methods to create particular document types. Each
        test suite extending this method can call thoses method to set up their testing environment in their
        own `setUpClass` method.
    """

    @classmethod
    def setUpClass(cls):
        """ This method set up the minimal requried part of chart of account """
        super(AccountTestNoChartCommon, cls).setUpClass()
        # To speed up test, create object without mail tracking
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}

        # Create base account to simulate a chart of account
        user_type_payable = cls.env.ref('account.data_account_type_payable')
        cls.account_payable = cls.env['account.account'].create({
            'code': 'NC1110',
            'name': 'Test Payable Account',
            'user_type_id': user_type_payable.id,
            'reconcile': True
        })
        user_type_receivable = cls.env.ref('account.data_account_type_receivable')
        cls.account_receivable = cls.env['account.account'].create({
            'code': 'NC1111',
            'name': 'Test Receivable Account',
            'user_type_id': user_type_receivable.id,
            'reconcile': True
        })

        # Create a customer
        Partner = cls.env['res.partner'].with_context(context_no_mail)
        cls.partner_customer_usd = Partner.create({
            'name': 'Customer from the North',
            'email': 'customer.usd@north.com',
            'property_account_payable_id': cls.account_payable.id,
            'property_account_receivable_id': cls.account_receivable.id,
            'company_id': cls.env.ref('base.main_company').id
        })

        cls.sale_journal0 = cls.env['account.journal'].create({
            'name': 'Sale Journal',
            'type': 'sale',
            'code': 'SJT0',
        })

        cls.general_journal0 = cls.env['account.journal'].create({
            'name': 'General Journal',
            'type': 'general',
            'code': 'GJT0',
        })

    @classmethod
    def setUpAdditionalAccounts(cls):
        """ Set up some addionnal accounts: expenses, revenue, ... """
        user_type_income = cls.env.ref('account.data_account_type_direct_costs')
        cls.account_income = cls.env['account.account'].create({
            'code': 'NC1112', 'name':
            'Sale - Test Account',
            'user_type_id': user_type_income.id
        })
        user_type_expense = cls.env.ref('account.data_account_type_expenses')
        cls.account_expense = cls.env['account.account'].create({
            'code': 'NC1113',
            'name': 'HR Expense - Test Purchase Account',
            'user_type_id': user_type_expense.id
        })
        user_type_revenue = cls.env.ref('account.data_account_type_revenue')
        cls.account_revenue = cls.env['account.account'].create({
            'code': 'NC1114',
            'name': 'Sales - Test Sales Account',
            'user_type_id': user_type_revenue.id,
            'reconcile': True
        })

    @classmethod
    def setUpAccountJournal(cls):
        """ Set up some journals: sale, purchase, ... """
        cls.journal_purchase = cls.env['account.journal'].create({
            'name': 'Purchase Journal - Test',
            'code': 'AJ-PURC',
            'type': 'purchase',
            'company_id': cls.env.user.company_id.id,
            'default_debit_account_id': cls.account_expense.id,
            'default_credit_account_id': cls.account_expense.id,
        })
        cls.journal_sale = cls.env['account.journal'].create({
            'name': 'Sale Journal - Test',
            'code': 'AJ-SALE',
            'type': 'sale',
            'company_id': cls.env.user.company_id.id,
            'default_debit_account_id': cls.account_income.id,
            'default_credit_account_id': cls.account_income.id,
        })
        cls.journal_general = cls.env['account.journal'].create({
            'name': 'General Journal - Test',
            'code': 'AJ-GENERAL',
            'type': 'general',
            'company_id': cls.env.user.company_id.id,
        })
        cls.journal_bank = cls.env['account.journal'].create({
            'name': 'Bank Journal - Test',
            'code': 'AJ-BANK',
            'type': 'bank',
            'company_id': cls.env.user.company_id.id,
        })

    @classmethod
    def setUpUsers(cls):
        """ Create 2 users: an employee and a manager. Both will have correct account configured
            on their partner. Others access rigths should be given in extending test suites set up.
        """
        group_employee = cls.env.ref('base.group_user')
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True})
        cls.user_employee = Users.create({
            'name': 'Tyrion Lannister Employee',
            'login': 'tyrion',
            'email': 'tyrion@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_employee.id])],
        })
        cls.user_manager = Users.create({
            'name': 'Daenerys Targaryen Manager',
            'login': 'daenerys',
            'email': 'daenerys@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_employee.id])],
        })
        account_values = {
            'property_account_payable_id': cls.account_payable.id,
            'property_account_receivable_id': cls.account_receivable.id,
        }
        cls.user_manager.partner_id.write(account_values)
        cls.user_employee.partner_id.write(account_values)

class AccountTestNoChartCommonMultiCompany(AccountTestNoChartCommon):
    """ Some tests required to be executed at module installation, and not 'post install', like moslty
        of accounting tests, since a chart of account is required
        This test setup class provides data for test suite to make business flow working without a chart
        of account installed in a multi-company environment.
        The class provide some helpers methods to create particular document types. Each test suite extending
        this method can call thoses method to set up their testing environment in their own `setUpClass` method.
    """

    @classmethod
    def setUpClass(cls):
        """ This method set up the minimal requried part of chart of account """
        super(AccountTestNoChartCommonMultiCompany, cls).setUpClass()
        cls.company_B = cls.env['res.company'].create({'name': 'Company B'})

        # To speed up test, create object without mail tracking
        context_no_mail = {'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True}

        # Create base account to simulate a chart of account
        user_type_payable = cls.env.ref('account.data_account_type_payable')
        cls.account_payable_company_B = cls.env['account.account'].create({
            'code': 'NC1110',
            'name': 'Test Payable Account Company B',
            'user_type_id': user_type_payable.id,
            'reconcile': True,
            'company_id': cls.company_B.id
        })

        user_type_receivable = cls.env.ref('account.data_account_type_receivable')
        cls.account_receivable_company_B = cls.env['account.account'].create({
            'code': 'NC1111',
            'name': 'Test Receivable Account Company B',
            'user_type_id': user_type_receivable.id,
            'reconcile': True,
            'company_id': cls.company_B.id
        })

        # Create a customer for each company
        Partner = cls.env['res.partner'].with_context(context_no_mail)
        cls.partner_customer_company_B = Partner.create({
            'name': 'Customer from the South',
            'email': 'customer@south.com',
            'property_account_payable_id': cls.account_payable_company_B.id,
            'property_account_receivable_id': cls.account_receivable_company_B.id,
            'company_id': cls.company_B.id
        })

    @classmethod
    def setUpAdditionalAccounts(cls):
        """ Set up some addionnal accounts: expenses, revenue, ... """
        super(AccountTestNoChartCommonMultiCompany, cls).setUpAdditionalAccounts()
        user_type_income = cls.env.ref('account.data_account_type_direct_costs')
        cls.account_income_company_B = cls.env['account.account'].create({
            'code': 'NC1112',
            'name': 'Sale - Test Account Company B',
            'user_type_id': user_type_income.id,
            'company_id': cls.company_B.id,
        })
        user_type_expense = cls.env.ref('account.data_account_type_expenses')
        cls.account_expense_company_B = cls.env['account.account'].create({
            'code': 'NC1113',
            'name': 'HR Expense - Test Purchase Account Company B',
            'user_type_id': user_type_expense.id,
            'company_id': cls.company_B.id,
        })
        user_type_revenue = cls.env.ref('account.data_account_type_revenue')
        cls.account_revenue_company_B = cls.env['account.account'].create({
            'code': 'NC1114',
            'name': 'Sales - Test Sales Account Company B',
            'user_type_id': user_type_revenue.id,
            'reconcile': True,
            'company_id': cls.company_B.id,
        })

    @classmethod
    def setUpAccountJournal(cls):
        """ Set up some journals: sale, purchase, ... """
        super(AccountTestNoChartCommonMultiCompany, cls).setUpAccountJournal()
        cls.journal_purchase_company_B = cls.env['account.journal'].create({
            'name': 'Purchase Journal Company B - Test',
            'code': 'AJ-PURC',
            'type': 'purchase',
            'company_id': cls.company_B.id,
            'default_debit_account_id': cls.account_expense_company_B.id,
            'default_credit_account_id': cls.account_expense_company_B.id,
        })
        cls.journal_sale_company_B = cls.env['account.journal'].create({
            'name': 'Sale Journal Company B - Test',
            'code': 'AJ-SALE',
            'type': 'sale',
            'company_id': cls.company_B.id,
            'default_debit_account_id': cls.account_income_company_B.id,
            'default_credit_account_id': cls.account_income_company_B.id,
        })
        cls.journal_general_company_B = cls.env['account.journal'].create({
            'name': 'General Journal Company B - Test',
            'code': 'AJ-GENERAL',
            'type': 'general',
            'company_id': cls.company_B.id,
        })

    @classmethod
    def setUpUsers(cls):
        """ Create 2 users for each company: an employee and a manager. Both will have correct account configured
            on their partner. Others access rigths should be given in extending test suites set up.
        """
        super(AccountTestNoChartCommonMultiCompany, cls).setUpUsers()
        group_employee = cls.env.ref('base.group_user')
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True})
        cls.user_employee_company_B = Users.create({
            'name': 'Gregor Clegane Employee',
            'login': 'gregor',
            'email': 'gregor@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_employee.id])],
            'company_id': cls.company_B.id,
            'company_ids': [cls.company_B.id],
        })
        cls.user_manager_company_B = Users.create({
            'name': 'Cersei Lannister Manager',
            'login': 'cersei',
            'email': 'cersei@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_employee.id])],
            'company_id': cls.company_B.id,
            'company_ids': [cls.company_B.id, cls.env.company.id],
        })
        cls.user_manager.write({
            'company_ids': [(6, 0, [cls.company_B.id, cls.env.company.id])],
        })
        account_values_company_B = {
            'property_account_payable_id': cls.account_payable_company_B.id,
            'property_account_receivable_id': cls.account_receivable_company_B.id,
        }
        cls.user_manager_company_B.partner_id.write(account_values_company_B)
        cls.user_employee_company_B.partner_id.write(account_values_company_B)


@tagged('post_install', '-at_install')
class AccountTestInvoicingCommon(SavepointCase):

    @classmethod
    def copy_account(cls, account):
        suffix_nb = 1
        while True:
            new_code = '%s (%s)' % (account.code, suffix_nb)
            if account.search_count([('company_id', '=', account.company_id.id), ('code', '=', new_code)]):
                suffix_nb += 1
            else:
                return account.copy(default={'code': new_code})

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(AccountTestInvoicingCommon, cls).setUpClass()

        chart_template = None
        if chart_template_ref:
            chart_template = cls.env.ref(chart_template_ref)
        if not chart_template:
            chart_template = cls.env.user.company_id.chart_template_id
        if not chart_template:
            chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)
        if not chart_template:
            cls.skipTest(cls, "Accounting Tests skipped because the user's company has no chart of accounts.")

        # Create user.
        user = cls.env['res.users'].create({
            'name': 'Because I am accountman!',
            'login': 'accountman',
            'groups_id': [(6, 0, cls.env.user.groups_id.ids), (4, cls.env.ref('account.group_account_user').id)],
        })
        user.partner_id.email = 'accountman@test.com'

        # Shadow the current environment/cursor with one having the report user.
        # This is mandatory to test access rights.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        cls.company_data = cls.setup_company_data('company_1_data')

        user.write({
            'company_ids': [(6, 0, cls.company_data['company'].ids)],
            'company_id': cls.company_data['company'].id,
        })

        cls.currency_data = cls.setup_multi_currency_data()

        # ==== Taxes ====
        cls.tax_sale_a = cls.company_data['default_tax_sale']
        cls.tax_sale_b = cls.company_data['default_tax_sale'].copy()
        cls.tax_purchase_a = cls.company_data['default_tax_purchase']
        cls.tax_purchase_b = cls.company_data['default_tax_purchase'].copy()
        cls.tax_armageddon = cls.setup_armageddon_tax('complex_tax', cls.company_data)

        # ==== Products ====
        cls.product_a = cls.env['product.product'].create({
            'name': 'product_a',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [(6, 0, cls.tax_sale_a.ids)],
            'supplier_taxes_id': [(6, 0, cls.tax_purchase_a.ids)],
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'product_b',
            'uom_id': cls.env.ref('uom.product_uom_dozen').id,
            'lst_price': 200.0,
            'standard_price': 160.0,
            'property_account_income_id': cls.copy_account(cls.company_data['default_account_revenue']).id,
            'property_account_expense_id': cls.copy_account(cls.company_data['default_account_expense']).id,
            'taxes_id': [(6, 0, (cls.tax_sale_a + cls.tax_sale_b).ids)],
            'supplier_taxes_id': [(6, 0, (cls.tax_purchase_a + cls.tax_purchase_b).ids)],
        })

        # ==== Fiscal positions ====
        cls.fiscal_pos_a = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': cls.tax_sale_a.id,
                    'tax_dest_id': cls.tax_sale_b.id,
                }),
                (0, None, {
                    'tax_src_id': cls.tax_purchase_a.id,
                    'tax_dest_id': cls.tax_purchase_b.id,
                }),
            ],
            'account_ids': [
                (0, None, {
                    'account_src_id': cls.product_a.property_account_income_id.id,
                    'account_dest_id': cls.product_b.property_account_income_id.id,
                }),
                (0, None, {
                    'account_src_id': cls.product_a.property_account_expense_id.id,
                    'account_dest_id': cls.product_b.property_account_expense_id.id,
                }),
            ],
        })

        # ==== Payment terms ====
        cls.pay_terms_a = cls.env.ref('account.account_payment_term_immediate')
        cls.pay_terms_b = cls.env['account.payment.term'].create({
            'name': '30% Advance End of Following Month',
            'note': 'Payment terms: 30% Advance End of Following Month',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 30.0,
                    'sequence': 400,
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
                (0, 0, {
                    'value': 'balance',
                    'value_amount': 0.0,
                    'sequence': 500,
                    'days': 31,
                    'option': 'day_following_month',
                }),
            ],
        })

        # ==== Partners ====
        cls.partner_a = cls.env['res.partner'].create({
            'name': 'partner_a',
            'property_payment_term_id': cls.pay_terms_a.id,
            'property_supplier_payment_term_id': cls.pay_terms_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'company_id': False,
        })
        cls.partner_b = cls.env['res.partner'].create({
            'name': 'partner_b',
            'property_payment_term_id': cls.pay_terms_b.id,
            'property_supplier_payment_term_id': cls.pay_terms_b.id,
            'property_account_position_id': cls.fiscal_pos_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].copy().id,
            'property_account_payable_id': cls.company_data['default_account_payable'].copy().id,
            'company_id': False,
        })

        # ==== Cash rounding ====
        cls.cash_rounding_a = cls.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.company_data['default_account_revenue'].copy().id,
            'loss_account_id': cls.company_data['default_account_expense'].copy().id,
            'rounding_method': 'UP',
        })
        cls.cash_rounding_b = cls.env['account.cash.rounding'].create({
            'name': 'biggest_tax',
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'DOWN',
        })

    @classmethod
    def setup_company_data(cls, company_name, **kwargs):
        ''' Create a new company having the name passed as parameter.
        A chart of accounts will be installed to this company: the same as the current company one.
        The current user will get access to this company.

        :param company_name: The name of the company.
        :return: A dictionary will be returned containing all relevant accounting data for testing.
        '''
        def search_account(company, chart_template, field_name, domain):
            template_code = chart_template[field_name].code
            domain = [('company_id', '=', company.id)] + domain

            account = None
            if template_code:
                account = cls.env['account.account'].search(domain + [('code', '=like', template_code + '%')], limit=1)

            if not account:
                account = cls.env['account.account'].search(domain, limit=1)
            return account

        chart_template = cls.env.user.company_id.chart_template_id
        currency = cls.env.user.company_id.currency_id
        company = cls.env['res.company'].create({
            'name': company_name,
            'currency_id': currency.id,
            **kwargs,
        })
        cls.env.user.company_ids |= company

        chart_template.with_company(company).try_loading()

        # The currency could be different after the installation of the chart template.
        company.write({'currency_id': kwargs.get('currency_id', currency.id)})

        return {
            'company': company,
            'currency': company.currency_id,
            'default_account_revenue': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id', '=', cls.env.ref('account.data_account_type_revenue').id)
                ], limit=1),
            'default_account_expense': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id', '=', cls.env.ref('account.data_account_type_expenses').id)
                ], limit=1),
            'default_account_receivable': search_account(company, chart_template, 'property_account_receivable_id', [
                ('user_type_id.type', '=', 'receivable')
            ]),
            'default_account_payable': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id.type', '=', 'payable')
                ], limit=1),
            'default_account_assets': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id', '=', cls.env.ref('account.data_account_type_current_assets').id)
                ], limit=1),
            'default_account_tax_sale': company.account_sale_tax_id.mapped('invoice_repartition_line_ids.account_id'),
            'default_account_tax_purchase': company.account_purchase_tax_id.mapped('invoice_repartition_line_ids.account_id'),
            'default_journal_misc': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'general')
                ], limit=1),
            'default_journal_sale': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'sale')
                ], limit=1),
            'default_journal_purchase': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'purchase')
                ], limit=1),
            'default_journal_bank': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'bank')
                ], limit=1),
            'default_journal_cash': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'cash')
                ], limit=1),
            'default_tax_sale': company.account_sale_tax_id,
            'default_tax_purchase': company.account_purchase_tax_id,
        }

    @classmethod
    def setup_multi_currency_data(cls, default_values={}, rate2016=3.0, rate2017=2.0):
        foreign_currency = cls.env['res.currency'].create({
            'name': 'Gold Coin',
            'symbol': '☺',
            'rounding': 0.001,
            'position': 'after',
            'currency_unit_label': 'Gold',
            'currency_subunit_label': 'Silver',
            **default_values,
        })
        rate1 = cls.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': rate2016,
            'currency_id': foreign_currency.id,
            'company_id': cls.env.company.id,
        })
        rate2 = cls.env['res.currency.rate'].create({
            'name': '2017-01-01',
            'rate': rate2017,
            'currency_id': foreign_currency.id,
            'company_id': cls.env.company.id,
        })
        return {
            'currency': foreign_currency,
            'rates': rate1 + rate2,
        }

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        return cls.env['account.tax'].create({
            'name': '%s (group)' % tax_name,
            'amount_type': 'group',
            'amount': 0.0,
            'children_tax_ids': [
                (0, 0, {
                    'name': '%s (child 1)' % tax_name,
                    'amount_type': 'percent',
                    'amount': 20.0,
                    'price_include': True,
                    'include_base_amount': True,
                    'tax_exigibility': 'on_invoice',
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'factor_percent': 40,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                        (0, 0, {
                            'factor_percent': 60,
                            'repartition_type': 'tax',
                            # /!\ No account set.
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'factor_percent': 40,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                        (0, 0, {
                            'factor_percent': 60,
                            'repartition_type': 'tax',
                            # /!\ No account set.
                        }),
                    ],
                }),
                (0, 0, {
                    'name': '%s (child 2)' % tax_name,
                    'amount_type': 'percent',
                    'amount': 10.0,
                    'tax_exigibility': 'on_payment',
                    'cash_basis_transition_account_id': company_data['default_account_tax_sale'].copy().id,
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'base',
                        }),

                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                }),
            ],
        })

    @classmethod
    def init_invoice(cls, move_type):
        move_form = Form(cls.env['account.move'].with_context(default_move_type=move_type))
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.partner_id = cls.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = cls.product_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = cls.product_b
        return move_form.save()

    def assertInvoiceValues(self, move, expected_lines_values, expected_move_values):
        def sort_lines(lines):
            return lines.sorted(lambda line: (line.exclude_from_invoice_tab, not bool(line.tax_line_id), line.name or '', line.balance))
        self.assertRecordValues(sort_lines(move.line_ids.sorted()), expected_lines_values)
        self.assertRecordValues(sort_lines(move.invoice_line_ids.sorted()), expected_lines_values[:len(move.invoice_line_ids)])
        self.assertRecordValues(move, [expected_move_values])


class TestAccountReconciliationCommon(AccountTestCommon):

    """Tests for reconciliation (account.tax)

    Test used to check that when doing a sale or purchase invoice in a different currency,
    the result will be balanced.
    """

    @classmethod
    def setUpClass(cls):
        super(TestAccountReconciliationCommon, cls).setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'A test company',
            'currency_id': cls.env.ref('base.EUR').id,
        })

        cls.env.user.company_id = cls.company
        cls.env.user.groups_id |= cls.env.ref('account.group_account_user')
        # Generate minimal data for my new company
        cls.create_accounting_minimal_data()

        cls.acc_bank_stmt_model = cls.env['account.bank.statement']
        cls.acc_bank_stmt_line_model = cls.env['account.bank.statement.line']
        cls.res_currency_model = cls.registry('res.currency')
        cls.res_currency_rate_model = cls.registry('res.currency.rate')

        cls.partner_agrolait = cls.env['res.partner'].create({
            'name': 'Deco Addict',
            'is_company': True,
            'country_id': cls.env.ref('base.us').id,
        })
        cls.partner_agrolait_id = cls.partner_agrolait.id
        cls.currency_swiss_id = cls.env.ref("base.CHF").id
        cls.currency_usd_id = cls.env.ref("base.USD").id
        cls.currency_euro_id = cls.env.ref("base.EUR").id
        # YTI FIXME Some of those lines should be useless now
        cls.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [cls.currency_euro_id, cls.company.id])
        cls.account_rcv = cls.partner_agrolait.property_account_receivable_id or cls.env['account.account'].search([('user_type_id', '=', cls.env.ref('account.data_account_type_receivable').id)], limit=1)
        cls.account_rsa = cls.partner_agrolait.property_account_payable_id or cls.env['account.account'].search([('user_type_id', '=', cls.env.ref('account.data_account_type_payable').id)], limit=1)
        cls.product = cls.env['product.product'].create({
            'name': 'Product Product 4',
            'standard_price': 500.0,
            'list_price': 750.0,
            'type': 'consu',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

        cls.bank_journal_euro = cls.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        cls.account_euro = cls.bank_journal_euro.default_debit_account_id

        cls.bank_journal_usd = cls.env['account.journal'].create({'name': 'Bank US', 'type': 'bank', 'code': 'BNK68', 'currency_id': cls.currency_usd_id})
        cls.account_usd = cls.bank_journal_usd.default_debit_account_id

        cls.fx_journal = cls.env['res.users'].browse(cls.env.uid).company_id.currency_exchange_journal_id
        cls.diff_income_account = cls.env['res.users'].browse(cls.env.uid).company_id.income_currency_exchange_account_id
        cls.diff_expense_account = cls.env['res.users'].browse(cls.env.uid).company_id.expense_currency_exchange_account_id

        cls.inbound_payment_method = cls.env['account.payment.method'].create({
            'name': 'inbound',
            'code': 'IN',
            'payment_type': 'inbound',
        })

        cls.expense_account = cls.env['account.account'].create({
            'name': 'EXP',
            'code': 'EXP',
            'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
            'company_id': cls.company.id,
        })
        # cash basis intermediary account
        cls.tax_waiting_account = cls.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'user_type_id': cls.env.ref('account.data_account_type_current_liabilities').id,
            'reconcile': True,
            'company_id': cls.company.id,
        })
        # cash basis final account
        cls.tax_final_account = cls.env['account.account'].create({
            'name': 'TAX_TO_DEDUCT',
            'code': 'TDEDUCT',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'company_id': cls.company.id,
        })
        cls.tax_base_amount_account = cls.env['account.account'].create({
            'name': 'TAX_BASE',
            'code': 'TBASE',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'company_id': cls.company.id,
        })

        # Journals
        cls.purchase_journal = cls.env['account.journal'].create({
            'name': 'purchase',
            'code': 'PURCH',
            'type': 'purchase',
            'default_credit_account_id': cls.a_expense.id,
            'default_debit_account_id': cls.a_expense.id,
        })
        cls.cash_basis_journal = cls.env['account.journal'].create({
            'name': 'CABA',
            'code': 'CABA',
            'type': 'general',
        })
        cls.general_journal = cls.env['account.journal'].create({
            'name': 'general',
            'code': 'GENE',
            'type': 'general',
        })

        # Tax Cash Basis
        cls.tax_cash_basis = cls.env['account.tax'].create({
            'name': 'cash basis 20%',
            'type_tax_use': 'purchase',
            'company_id': cls.company.id,
            'amount': 20,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': cls.tax_waiting_account.id,
            'cash_basis_base_account_id': cls.tax_base_amount_account.id,
            'invoice_repartition_line_ids': [
                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),

                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': cls.tax_final_account.id,
                    }),
                ],
            'refund_repartition_line_ids': [
                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),

                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': cls.tax_final_account.id,
                    }),
                ],
        })
        cls.env['res.currency.rate'].create([
            {
                'currency_id': cls.env.ref('base.EUR').id,
                'name': '2010-01-02',
                'rate': 1.0,
            }, {
                'currency_id': cls.env.ref('base.USD').id,
                'name': '2010-01-02',
                'rate': 1.2834,
            }, {
                'currency_id': cls.env.ref('base.USD').id,
                'name': time.strftime('%Y-06-05'),
                'rate': 1.5289,
            }
        ])

    def _create_invoice(self, type='out_invoice', invoice_amount=50, currency_id=None, partner_id=None, date_invoice=None, payment_term_id=False, auto_validate=False):
        date_invoice = date_invoice or time.strftime('%Y') + '-07-01'

        invoice_vals = {
            'move_type': type,
            'partner_id': partner_id or self.partner_agrolait_id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'invoice_line_ids': [(0, 0, {
                'name': 'product that cost %s' % invoice_amount,
                'quantity': 1,
                'price_unit': invoice_amount,
                'tax_ids': [(6, 0, [])],
            })]
        }

        if payment_term_id:
            invoice_vals['invoice_payment_term_id'] = payment_term_id

        if currency_id:
            invoice_vals['currency_id'] = currency_id

        invoice = self.env['account.move'].with_context(default_move_type=type).create(invoice_vals)
        if auto_validate:
            invoice.post()
        return invoice

    def create_invoice(self, type='out_invoice', invoice_amount=50, currency_id=None):
        return self._create_invoice(type=type, invoice_amount=invoice_amount, currency_id=currency_id, auto_validate=True)

    def create_invoice_partner(self, type='out_invoice', invoice_amount=50, currency_id=None, partner_id=False, payment_term_id=False):
        return self._create_invoice(
            type=type,
            invoice_amount=invoice_amount,
            currency_id=currency_id,
            partner_id=partner_id,
            payment_term_id=payment_term_id,
            auto_validate=True
        )

    def make_payment(self, invoice_record, bank_journal, amount=0.0, amount_currency=0.0, currency_id=None, reconcile_param=[]):
        bank_stmt = self.acc_bank_stmt_model.create({
            'journal_id': bank_journal.id,
            'date': time.strftime('%Y') + '-07-15',
            'name': 'payment' + invoice_record.name,
            'line_ids': [(0, 0, {
                'payment_ref': 'payment',
                'partner_id': self.partner_agrolait_id,
                'amount': amount,
                'amount_currency': amount_currency,
                'foreign_currency_id': currency_id,
            })],
        })
        bank_stmt.button_post()

        bank_stmt.line_ids[0].reconcile(reconcile_param)
        return bank_stmt

    def make_customer_and_supplier_flows(self, invoice_currency_id, invoice_amount, bank_journal, amount, amount_currency, transaction_currency_id):
        #we create an invoice in given invoice_currency
        invoice_record = self.create_invoice(type='out_invoice', invoice_amount=invoice_amount, currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        line = invoice_record.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=amount, amount_currency=amount_currency, currency_id=transaction_currency_id, reconcile_param=[{'id': line.id}])
        customer_move_lines = bank_stmt.line_ids.line_ids

        #we create a supplier bill in given invoice_currency
        invoice_record = self.create_invoice(type='in_invoice', invoice_amount=invoice_amount, currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        line = invoice_record.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=-amount, amount_currency=-amount_currency, currency_id=transaction_currency_id, reconcile_param=[{'id': line.id}])
        supplier_move_lines = bank_stmt.line_ids.line_ids
        return customer_move_lines, supplier_move_lines
