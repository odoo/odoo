from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged, HttpCase


@tagged('-at_install', 'post_install')
class TestUi(TestExpenseCommon, HttpCase):
    browser_size = "1920,1080"

    def test_show_expense_receipt_on_expense_line_click(self):
        expense_1, expense_2, expense_3 = self.env['hr.expense'].create([
            {
                'name': 'expense_1',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 1000,
            },
            {
                'name': 'expense_2',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 999,
            },
            {
                'name': 'expense_3',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 998,
            },
        ])
        attachment_1, attachment_2, attachment_3 = self.env['ir.attachment'].create([
            {
                'name': "test_file_1.png",
                'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=1",
                'res_id': expense_1.id,
                'res_model': 'hr.expense',
            },
            {
                'name': "test_file_2.png",
                'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=2",
                'res_id': expense_2.id,
                'res_model': 'hr.expense',
            },
            {
                'name': "test_file_3.png",
                'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=3",
                'res_id': expense_3.id,
                'res_model': 'hr.expense',
            },
        ])

        expense_1.message_main_attachment_id = attachment_1
        expense_2.message_main_attachment_id = attachment_2
        expense_3.message_main_attachment_id = attachment_3

        self.env['hr.expense.sheet'].create({
            'employee_id': self.expense_employee.id,
            'name': 'test sheet',
            'expense_line_ids': [Command.set([expense_1.id, expense_2.id, expense_3.id])],
        })

        self.start_tour('/web', 'show_expense_receipt_tour', login=self.env.user.login)
