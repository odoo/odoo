# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestExpenseCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        group_expense_manager = cls.env.ref('hr_expense.group_hr_expense_manager')

        cls.expense_user_employee = mail_new_test_user(
            cls.env,
            name='expense_user_employee',
            login='expense_user_employee',
            email='expense_user_employee@example.com',
            notification_type='email',
            groups='base.group_user',
            company_ids=[(6, 0, cls.env.companies.ids)],
        )
        cls.expense_user_manager = mail_new_test_user(
            cls.env,
            name='Expense manager',
            login='expense_manager_1',
            email='expense_manager_1@example.com',
            notification_type='email',
            groups='base.group_user,hr_expense.group_hr_expense_manager',
            company_ids=[(6, 0, cls.env.companies.ids)],
        )

        cls.expense_employee = cls.env['hr.employee'].create({
            'name': 'expense_employee',
            'user_id': cls.expense_user_employee.id,
            'address_home_id': cls.expense_user_employee.partner_id.id,
            'address_id': cls.expense_user_employee.partner_id.id,
        })

        # Allow the current accounting user to access the expenses.
        cls.env.user.groups_id |= group_expense_manager

        # Create analytic account
        cls.analytic_plan = cls.env['account.analytic.plan'].create({'name': 'Plan Test', 'company_id': False})
        cls.analytic_account_1 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_1',
            'plan_id': cls.analytic_plan.id,
        })
        cls.analytic_account_2 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_2',
            'plan_id': cls.analytic_plan.id,
        })

        # Ensure products can be expensed.
        (cls.product_a + cls.product_b).write({'can_be_expensed': True})
        # Taxes on the products are included in price
        (cls.product_a.supplier_taxes_id + cls.product_b.supplier_taxes_id).write({'price_include': True})
        cls.company_data['default_tax_purchase'].write({'price_include': True})
