# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, tagged, new_test_user

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged('-at_install', 'post_install')
class TestExpensesAccessRights(TestExpenseCommon, HttpCase):

    def test_expense_access_rights(self):
        """ The expense employee can't be able to create an expense for someone else. """

        expense_employee_2 = self.env['hr.employee'].sudo().create({
            'name': 'expense_employee_2',
            'user_id': self.env.user.id,
            'work_contact_id': self.env.user.partner_id.id,
        }).sudo(False)

        with self.assertRaises(AccessError):
            self.env['hr.expense'].with_user(self.expense_user_employee).create({
                'name': "Superboy costume washing",
                'employee_id': expense_employee_2.id,
                'product_id': self.product_a.id,
                'quantity': 1,
                'price_unit': 1,
            })

    def test_expense_access_rights_user(self):
        # The expense base user (without other rights) is able to create and read sheet

        user = new_test_user(self.env, login='test-expense', groups='base.group_user')
        expense_employee = self.env['hr.employee'].sudo().create({
            'name': 'expense_employee_base_user',
            'user_id': user.id,
            'work_contact_id': user.partner_id.id,
            'expense_manager_id': self.expense_user_manager.id,
            'address_id': user.partner_id.id,
        }).sudo(False)

        expense = self.env['hr.expense'].with_user(user).create({
            'name': 'First Expense for employee',
            'employee_id': expense_employee.id,
            # Expense without foreign currency but analytic account.
            'product_id': self.product_a.id,
            'price_unit': 1000.0,
        })
        self.start_tour("/odoo", 'hr_expense_access_rights_test_tour', login="test-expense")
        self.assertRecordValues(expense, [{'state': 'submitted'}])

    def test_expense_create_and_post_message_on_submitted(self):
        """ Test than different users can post (or not) a message and an attachment when the expense is submitted.
        """

        standard_user = self.expense_user_employee
        another_standard_user = new_test_user(self.env, login='another_standard_user', groups='base.group_user')
        standard_user_manager = self.expense_user_manager
        admin_user = self.env.ref('base.user_admin')
        admin_user.company_ids |= self.env.companies

        expense = self.env['hr.expense'].with_user(standard_user).create({
            'name': "Superboy costume washing",
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
            'quantity': 1,
            'price_unit': 1,
        })

        expense.with_user(standard_user).action_submit()

        expense.with_user(standard_user).message_post(body="Standard user posts a message on his own expense.")
        with self.assertRaises(AccessError):
            expense.with_user(another_standard_user).message_post(body="Another standard user tries to post a message on the expense.")
        expense.with_user(standard_user_manager).message_post(body="Manager user posts a message on the expense.")
        expense.with_user(admin_user).message_post(body="Admin user posts a message on the expense.")

        self.assertEqual(len(expense.message_ids), 3)

        # When testing for uploading the attachments, we cant simulate it through a tour as using inputFiles isn't possible
        # with a AttachDocumentWidget since the input isn't added to the DOM.
        self.authenticate(standard_user.login, standard_user.login)
        response_user = self.url_open("/mail/attachment/upload",
            {
            "csrf_token": http.Request.csrf_token(self),
            "thread_id": expense.id,
            "thread_model": "hr.expense",
            },
            files={'ufile': ('salut.txt', b"Salut !\n", 'text/plain')},
        )
        expense.with_user(standard_user).attach_document(attachment_ids=[data['id'] for data in response_user.json()['data']['ir.attachment']])
        self.assertEqual(response_user.status_code, 200)
        self.assertEqual(len(expense.attachment_ids), 1)
        self.assertEqual(expense.message_main_attachment_id.id, response_user.json()['data']['ir.attachment'][0]['id'])

        self.authenticate(another_standard_user.login, another_standard_user.login)
        response_user2 = self.url_open("/mail/attachment/upload",
            {
            "csrf_token": http.Request.csrf_token(self),
            "thread_id": expense.id,
            "thread_model": "hr.expense",
            },
            files={'ufile': ('fail.txt', b"Fail\n", 'text/plain')},
        )
        with self.assertRaises(AccessError):
            expense.with_user(another_standard_user).attach_document(attachment_ids=None)
        self.assertEqual(response_user2.status_code, 404)
        self.assertEqual(len(expense.attachment_ids), 1)  # No new attachment
        self.assertEqual(expense.message_main_attachment_id.id, response_user.json()['data']['ir.attachment'][0]['id'])

        self.authenticate(standard_user_manager.login, standard_user_manager.login)
        response_manager = self.url_open("/mail/attachment/upload",
            {
            "csrf_token": http.Request.csrf_token(self),
            "thread_id": expense.id,
            "thread_model": "hr.expense",
            },
            files={'ufile': ('manager.txt', b"Manager\n", 'text/plain')},
        )
        expense.with_user(standard_user_manager).attach_document(attachment_ids=[data['id'] for data in response_manager.json()['data']['ir.attachment']])
        self.assertEqual(response_manager.status_code, 200)
        self.assertEqual(len(expense.attachment_ids), 2)
        self.assertEqual(expense.message_main_attachment_id.id, response_manager.json()['data']['ir.attachment'][0]['id'])

        self.authenticate(admin_user.login, admin_user.login)
        response_admin = self.url_open("/mail/attachment/upload",
            {
            "csrf_token": http.Request.csrf_token(self),
            "thread_id": expense.id,
            "thread_model": "hr.expense",
            },
            files={'ufile': ('admin.txt', b"Admin\n", 'text/plain')},
        )
        expense.with_user(admin_user).attach_document(attachment_ids=[data['id'] for data in response_admin.json()['data']['ir.attachment']])
        self.assertEqual(response_admin.status_code, 200)
        self.assertEqual(len(expense.attachment_ids), 3)
        self.assertEqual(expense.message_main_attachment_id.id, response_admin.json()['data']['ir.attachment'][0]['id'])

    def test_expense_user_cant_approve_own_expense(self):
        expense = self.env['hr.expense'].with_user(self.expense_user_employee).create({
            'name': "Superboy costume washing",
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
            'quantity': 1,
            'price_unit': 1,
        })
        expense.with_user(self.expense_user_employee).action_submit()
        with self.assertRaises(UserError):
            expense.with_user(self.expense_user_employee).action_approve()

    def test_expense_team_approver_cant_approve_expense_of_employee_he_does_not_manage(self):
        another_standard_user = new_test_user(self.env, login='another_standard_user', groups='base.group_user')
        another_standard_user_team_approver = new_test_user(self.env, login='another_standard_user_manager', groups='base.group_user,hr_expense.group_hr_expense_team_approver')

        another_employee = self.env['hr.employee'].sudo().create({
            'name': 'another_employee',
            'user_id': another_standard_user.id,
            'work_contact_id': another_standard_user.partner_id.id,
            'expense_manager_id': self.expense_user_manager.id,
        }).sudo(False)

        expense = self.env['hr.expense'].with_user(another_standard_user).create({
            'name': "Superboy costume washing",
            'employee_id': another_employee.id,
            'product_id': self.product_a.id,
            'quantity': 1,
            'price_unit': 1,
        })
        expense.with_user(another_standard_user).action_submit()
        with self.assertRaises(AccessError):
            expense.with_user(another_standard_user_team_approver).action_approve()
