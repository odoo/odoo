# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestExpenseCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True})
        group_user = cls.env.ref('base.group_user')
        group_expense_manager = cls.env.ref('hr_expense.group_hr_expense_manager')

        cls.expense_user_employee = Users.create({
            'name': 'expense_user_employee',
            'login': 'expense_user_employee',
            'email': 'expense_user_employee@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, group_user.ids)],
            'company_ids': [(6, 0, cls.env.companies.ids)],
        })
        cls.expense_user_manager = Users.create({
            'name': 'Expense manager',
            'login': 'expense_manager_1',
            'email': 'expense_manager_1@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, (group_user + group_expense_manager).ids)],
            'company_ids': [(6, 0, cls.env.companies.ids)],
        })

        cls.expense_employee = cls.env['hr.employee'].create({
            'name': 'expense_employee',
            'user_id': cls.expense_user_employee.id,
            'address_home_id': cls.expense_user_employee.partner_id.id,
            'address_id': cls.expense_user_employee.partner_id.id,
        })

        # Allow the current accounting user to access the expenses.
        cls.env.user.groups_id |= group_expense_manager

        # Create analytic account
        cls.analytic_account_1 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_1',
        })
        cls.analytic_account_2 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_2',
        })

        # Ensure products can be expensed.
        (cls.product_a + cls.product_b).write({'can_be_expensed': True})
