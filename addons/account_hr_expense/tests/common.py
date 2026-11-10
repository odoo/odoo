# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.hr_expense.tests.common import TestExpenseCommon


class TestAccountExpenseCommon(AccountTestInvoicingCommon, TestExpenseCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data_2 = cls.collect_company_accounting_data(cls.company_2)
        cls.product_category.with_company(cls.company_2).write({
            'property_account_income_categ_id': cls.company_data_2['default_account_revenue'].id,
            'property_account_expense_categ_id': cls.company_data_2['default_account_expense'].id,
        })

        # The products of the accounting common replaced the ones of the expenses
        (cls.product_a + cls.product_b).write({'can_be_expensed': True})
        cls.product_a.default_code = 'product_a'
        cls.product_b.default_code = 'product_b'
        cls.product_c.write({
            'property_account_income_id': cls.copy_account(cls.company_data['default_account_revenue']).id,
            'property_account_expense_id': cls.copy_account(cls.company_data['default_account_expense']).id,
            'taxes_id': [Command.set((cls.tax_sale_a + cls.tax_sale_b).ids)],
            'supplier_taxes_id': [Command.set((cls.tax_purchase_a + cls.tax_purchase_b).ids)],
        })

        # The employee needs a bank account to be paid
        cls.expense_employee.sudo().write({
            'bank_account_ids': [
                Command.create({
                    'account_number': 'BE68539007547034',
                    'allow_out_payment': True,
                    'partner_id': cls.expense_user_employee.partner_id.id,
                }),
            ],
        })

        # create expense account
        cls.expense_account = cls.env['account.account'].create({
            'code': '610010',
            'name': 'Expense Account 1',
        })

    def post_expenses(self, expenses):
        """
        Helper to "post" expenses (it actually post draft moves related to expenses),
        whether it's company or employee paid expenses
        """
        company_expenses, employee_expenses = expenses.partitioned(lambda expense: expense.payment_mode == 'company_account')
        if company_expenses:
            # post through payment to post both payment and move
            company_expenses.account_move_id.origin_payment_id.action_post()
        if employee_expenses:
            employee_expenses.account_move_id.action_post()

    def get_new_payment(self, expenses, amount):
        """ Helper to create payments """
        ctx = {'active_model': 'account.move', 'active_ids': expenses.account_move_id.ids}
        with freeze_time(self.frozen_today):
            payment_register = self.env['account.payment.register'].with_context(**ctx).create({
                'amount': amount,
                'journal_id': self.company_data['default_journal_bank'].id,
                'payment_method_line_id': self.inbound_payment_method_line.id,
            })
            self.assertEqual(payment_register.partner_bank_id.partner_id, expenses.employee_id.work_contact_id)
            return payment_register._create_payments()
