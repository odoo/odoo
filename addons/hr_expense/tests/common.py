# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestExpenseCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data_2 = cls.setup_other_company()
        cls.other_currency = cls.setup_other_currency('HRK')

        group_expense_manager = cls.env.ref('hr_expense.group_hr_expense_manager')

        cls.expense_user_employee = mail_new_test_user(
            cls.env,
            name='expense_user_employee',
            login='expense_user_employee',
            email='expense_user_employee@example.com',
            notification_type='email',
            groups='base.group_user',
            company_ids=[Command.set(cls.env.companies.ids)],
        )
        cls.expense_user_manager = mail_new_test_user(
            cls.env,
            name='Expense manager',
            login='expense_manager_1',
            email='expense_manager_1@example.com',
            notification_type='email',
            groups='base.group_user,hr_expense.group_hr_expense_manager',
            company_ids=[Command.set(cls.env.companies.ids)],
        )

        cls.expense_user_manager_2 = mail_new_test_user(
            cls.env,
            name='Expense manager',
            login='expense_manager_2',
            email='expense_manager_2@example.com',
            notification_type='email',
            groups='base.group_user,hr_expense.group_hr_expense_manager',
            company_ids=[Command.set(cls.env.companies.ids)],
        )

        cls.expense_employee = cls.env['hr.employee'].sudo().create({
            'name': 'expense_employee',
            'user_id': cls.expense_user_employee.id,
            'expense_manager_id': cls.expense_user_manager.id,
            'work_contact_id': cls.expense_user_employee.partner_id.id,
        }).sudo(False)

        # Allow the current accounting user to access the expenses.
        cls.env.user.group_ids |= group_expense_manager

        # Create analytic account
        cls.analytic_plan = cls.env['account.analytic.plan'].create({'name': 'Expense Plan Test'})
        cls.analytic_account_1 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_1',
            'plan_id': cls.analytic_plan.id,
        })
        cls.analytic_account_2 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_2',
            'plan_id': cls.analytic_plan.id,
        })

        # Create product without cost
        cls.product_c = cls.env['product.product'].create({
            'name': 'product_c with no cost',
            'uom_id': cls.env.ref('uom.product_uom_dozen').id,
            'lst_price': 200.0,
            'property_account_income_id': cls.copy_account(cls.company_data['default_account_revenue']).id,
            'property_account_expense_id': cls.copy_account(cls.company_data['default_account_expense']).id,
            'taxes_id': [Command.set((cls.tax_sale_a + cls.tax_sale_b).ids)],
            'supplier_taxes_id': [Command.set((cls.tax_purchase_a + cls.tax_purchase_b).ids)],
            'can_be_expensed': True,
            'default_code': 'product_c',
        })

        # Ensure Invoicing tests products can be expensed and their code is properly set.
        (cls.product_a + cls.product_b).write({'can_be_expensed': True})
        cls.product_a.default_code = 'product_a'
        cls.product_b.default_code = 'product_b'

        cls.frozen_today = datetime(year=2022, month=1, day=25, hour=0, minute=0, second=0)

        # create expense account
        cls.expense_account = cls.env['account.account'].create({
            'code': '610010',
            'name': 'Expense Account 1'
        })

    @classmethod
    def create_expenses(cls, values=None):
        if values is None or isinstance(values, dict):
            values = [values or {}]

        default_values = {
            'employee_id': cls.expense_employee.id,
            'date': cls.frozen_today.isoformat(),
            'company_id': cls.company_data['company'].id,
            'currency_id': cls.company_data['currency'].id,
        }

        default_product_values = {
            'product_id': cls.product_c.id,
            'total_amount_currency': 1000.00,
        }
        create_values = []
        for value_dict in values:
            if 'product_id' not in value_dict:
                default_values.update(default_product_values)
            value_dict = {**default_values, **(value_dict or {})}
            create_values.append(value_dict)
        return cls.env['hr.expense'].create(create_values).sorted()

    @classmethod
    def post_expenses_with_wizard(cls, expenses, journal=None, date=None):
        action = expenses.action_post()
        if action:
            wizard = expenses.env['hr.expense.post.wizard'].with_context(action['context']).browse(action['res_id'])
            if journal:
                wizard.employee_journal_id = journal.id
            wizard.accounting_date = date or fields.Date.context_today(expenses)
            wizard.action_post_entry()

    def get_new_payment(self, expenses, amount):
        """ Helper to create payments """
        ctx = {'active_model': 'account.move', 'active_ids': expenses.account_move_id.ids}
        with freeze_time(self.frozen_today):
            payment_register = self.env['account.payment.register'].with_context(**ctx).create({
                'amount': amount,
                'journal_id': self.company_data['default_journal_bank'].id,
                'payment_method_line_id': self.inbound_payment_method_line.id,
            })
            return payment_register._create_payments()
