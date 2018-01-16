# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_no_chart import TestAccountNoChartCommon


class TestExpenseCommon(TestAccountNoChartCommon):

    @classmethod
    def setUpClass(cls):
        super(TestExpenseCommon, cls).setUpClass()

        cls.setUpUsers()

        # The user manager is only expense manager
        user_group_manager = cls.env.ref('hr_expense.group_hr_expense_manager')
        cls.user_manager.write({
            'groups_id': [(6, 0, [user_group_manager.id])],
        })

        # create employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Johnny Employee',
            'address_home_id': cls.user_employee.partner_id.id,
            'address_id': cls.user_employee.partner_id.id,
        })

        # Create tax
        cls.tax = cls.env['account.tax'].create({
            'name': 'Expense 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
        })

        # Create analytic account
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test Analytic Account for Expenses',
        })

        # Expense reports
        cls.journal = cls.env['account.journal'].create({
            'name': 'Purchase Journal - Test',
            'code': 'HRTPJ',
            'type': 'purchase',
            'company_id': cls.env.user.company_id.id,
        })
        cls.expense_sheet = cls.env['hr.expense.sheet'].create({
            'name': 'Expense for Johnny Employee',
            'employee_id': cls.employee.id,
            'journal_id': cls.journal.id,
        })
