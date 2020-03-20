# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase
from odoo.addons.account.tests.account_test_no_chart import TestAccountNoChartCommon


class TestAccountMultiCompanyNoChartCommon(TestAccountNoChartCommon):
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
        super(TestAccountMultiCompanyNoChartCommon, cls).setUpClass()
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
        super(TestAccountMultiCompanyNoChartCommon, cls).setUpAdditionalAccounts()
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
        super(TestAccountMultiCompanyNoChartCommon, cls).setUpAccountJournal()
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
        super(TestAccountMultiCompanyNoChartCommon, cls).setUpUsers()
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
