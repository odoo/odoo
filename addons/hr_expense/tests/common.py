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
            'groups_id': [(6, 0, [user_group_manager.id, cls.env.ref('base.group_user').id])],
        })

        # create employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Johnny Employee',
            'user_id': cls.user_employee.id,
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
        cls.expense_sheet2 = cls.env['hr.expense.sheet'].create({
            'name': 'Second Expense for Johnny Employee',
            'employee_id': cls.employee.id,
            'journal_id': cls.journal.id,
        })

        Users = cls.env['res.users'].with_context(no_reset_password=True)

        # Find Employee group
        group_employee_id = cls.env.ref('base.group_user').id

        cls.user_emp2 = Users.create({
            'name': 'Superboy Employee',
            'login': 'superboy',
            'email': 'superboy@example.com',
            'groups_id': [(6, 0, [group_employee_id])]
        })

        cls.user_officer = Users.create({
            'name': 'Batman Officer',
            'login': 'batman',
            'email': 'batman.hero@example.com',
            'groups_id': [(6, 0, [group_employee_id, cls.env.ref('hr_expense.group_hr_expense_user').id])]
        })

        cls.emp_emp2 = cls.env['hr.employee'].create({
            'name': 'Superboy',
            'user_id': cls.user_emp2.id,
        })

        cls.emp_officer = cls.env['hr.employee'].create({
            'name': 'Batman',
            'user_id': cls.user_officer.id,
        })

        cls.emp_manager = cls.env['hr.employee'].create({
            'name': 'Superman',
            'user_id': cls.user_manager.id,
        })

        cls.rd = cls.env['hr.department'].create({
            'name': 'R&D',
            'manager_id': cls.emp_officer.id,
            'member_ids': [(6, 0, [cls.employee.id])],
        })

        cls.ps = cls.env['hr.department'].create({
            'name': 'PS',
            'manager_id': cls.emp_manager.id,
            'member_ids': [(6, 0, [cls.emp_emp2.id])],
        })

        cls.uom_unit = cls.env.ref('uom.product_uom_unit').id
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen').id

        cls.product_1 = cls.env['product.product'].create({
            'name': 'Batmobile repair',
            'type': 'service',
            'uom_id': cls.uom_unit,
            'uom_po_id': cls.uom_unit,
        })

        cls.product_2 = cls.env['product.product'].create({
            'name': 'Superboy costume washing',
            'type': 'service',
            'uom_id': cls.uom_unit,
            'uom_po_id': cls.uom_unit,
        })
