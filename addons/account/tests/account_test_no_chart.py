# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase


class TestAccountNoChartCommon(SavepointCase):
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
        super(TestAccountNoChartCommon, cls).setUpClass()
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
            'customer': True,
            'property_account_payable_id': cls.account_payable.id,
            'property_account_receivable_id': cls.account_receivable.id,
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
        })
        cls.journal_sale = cls.env['account.journal'].create({
            'name': 'Sale Journal - Test',
            'code': 'AJ-SALE',
            'type': 'sale',
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
