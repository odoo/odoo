# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class CommonTest(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(CommonTest, cls).setUpClass()

        # Create payable account for the expense
        user_type = cls.env.ref('account.data_account_type_payable')
        cls.account_payable = cls.env['account.account'].create({
            'code': 'X1111',
            'name': 'HR Expense - Test Payable Account',
            'user_type_id': user_type.id,
            'reconcile': True
        })

        # Create expenses account for the expense
        user_type = cls.env.ref('account.data_account_type_expenses')
        cls.account_expense = cls.env['account.account'].create({
            'code': 'X2120',
            'name': 'HR Expense - Test Purchase Account',
            'user_type_id': user_type.id
        })

        # User groups
        user_group_employee = cls.env.ref('base.group_user')
        user_group_manager = cls.env.ref('hr_expense.group_hr_expense_manager')

        # User and Employee Data
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True, 'mail_create_nolog': True})
        cls.user_employee = Users.create({
            'name': 'Johnny Employee',
            'login': 'john',
            'email': 'john@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [user_group_employee.id])],
        })
        cls.user_manager = Users.create({
            'name': 'Robert Manager',
            'login': 'rob',
            'email': 'rob@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [user_group_manager.id])],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Johnny Employee',
            'address_home_id': cls.user_employee.partner_id.id,
            'address_id': cls.user_employee.partner_id.id,
        })
        cls.user_manager.partner_id.write({'property_account_payable_id': cls.account_payable.id})
        cls.user_employee.partner_id.write({'property_account_payable_id': cls.account_payable.id})

        # Expense Products
        cls.product_ordered_cost = cls.env['product.product'].create({
            'name': "Ordered at cost",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'cost',
            'default_code': 'CONSU-ORDERED1',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense.id,
        })

        cls.product_deliver_cost = cls.env['product.product'].create({
            'name': "Delivered at cost",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'delivery',
            'expense_policy': 'cost',
            'default_code': 'CONSU-DELI1',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense.id,
        })

        cls.product_order_sales_price = cls.env['product.product'].create({
            'name': "Ordered at sales price",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'sales_price',
            'default_code': 'CONSU-ORDERED2',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense.id,
        })

        cls.product_deliver_sales_price = cls.env['product.product'].create({
            'name': "Delivered at sales price",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'delivery',
            'expense_policy': 'sales_price',
            'default_code': 'CONSU-DELI2',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense.id,
        })

        cls.product_no_expense = cls.env['product.product'].create({
            'name': "No expense",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'delivery',
            'expense_policy': 'no',
            'default_code': 'CONSU-NO',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense.id,
        })

        # Expense report
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
