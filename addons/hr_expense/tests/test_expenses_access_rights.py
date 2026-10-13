# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, new_test_user, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged('-at_install', 'post_install')
class TestExpensesAccessRights(TestExpenseCommon, HttpCase):

    _test_user_groups = None  # FIXME list needed groups

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
            })

        expense = self.env['hr.expense'].with_user(self.expense_user_employee).create({
            'name': 'expense_1',
            'date': '2016-01-01',
            'product_id': self.product_a.id,
            'quantity': 10.0,
            'employee_id': self.expense_employee.id,
        })

        # The expense employee shouldn't be able to bypass the submit state.
        with self.assertRaises(UserError):
            expense.with_user(self.expense_user_employee).state = 'approved'
        expense.with_user(self.expense_user_employee).state = 'draft'  # Should not raise

        expense.with_user(self.expense_user_employee).action_submit()
        self.assertEqual(expense.state, 'submitted')

        # Employee can also revert from the submitted state to a draft state
        expense.with_user(self.expense_user_employee).action_reset()
        self.assertEqual(expense.state, 'draft')

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

    def test_expense_create_and_post_message_on_submitted_and_approved(self):
        """ Test than different users can post (or not) a message and an attachment when the expense is submitted.
        And once it's approved, only someone using sudo should be able to post/delete an attachment on the expense.
        """

        standard_user = self.expense_user_employee
        another_standard_user = new_test_user(self.env, login='another_standard_user', groups='base.group_user')
        standard_user_manager = self.expense_user_manager
        admin_user = self.expense_user_manager_2
        admin_user.group_ids |= self.env.ref('base.group_system')
        admin_user.company_ids |= self.env.companies

        expense = self.env['hr.expense'].with_user(standard_user).create({
            'name': "Superboy costume washing",
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
            'quantity': 1,
        })

        expense.with_user(standard_user).action_submit()

        expense.with_user(standard_user).message_post(body="Standard user posts a message on his own expense.")
        with self.assertRaises(AccessError):
            expense.with_user(another_standard_user).message_post(body="Another standard user tries to post a message on the expense.")
        expense.with_user(standard_user_manager).message_post(body="Manager user posts a message on the expense.")
        expense.with_user(admin_user).message_post(body="Admin user posts a message on the expense.")

        self.assertEqual(len(expense.message_ids), 3)

        def upload_receipt(user, name, content):
            self.authenticate(user.login, user.login)
            return self.url_open(
                "/web/dataset/call_upload",
                {
                    'csrf_token': self.csrf_token(),
                    'model': 'hr.expense',
                    'method': 'attach_document',
                    'res_ids': json.dumps([expense.id]),
                },
                files={'ufile': (name, content, 'text/plain')},
            )

        # User that created the expense should be able to upload an attachment on the expense.
        # But he shouldn't be able to delete it once it's submitted
        user_response = upload_receipt(standard_user, 'salut.txt', b"Salut !\n")
        self.assertEqual(user_response.status_code, 200)
        self.assertFalse(user_response.json().get('error'))
        self.assertEqual(len(expense.attachment_ids), 1)
        self.assertEqual(expense.message_main_attachment_id.name, 'salut.txt')
        user_attachment = expense.message_main_attachment_id

        with self.assertRaises(UserError):
            expense.with_user(standard_user).attachment_ids.unlink()

        # User without any access to the expense shouldn't be able to upload an attachment on the expense.
        response = upload_receipt(another_standard_user, 'fail.txt', b"Fail\n")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['error']['message'])
        self.assertEqual(len(expense.attachment_ids), 1)  # No new attachment
        self.assertEqual(expense.message_main_attachment_id, user_attachment)

        # The manager should be able to upload and delete an attachment on the expense.
        manager_response = upload_receipt(standard_user_manager, 'manager.txt', b"Manager\n")
        self.assertEqual(manager_response.status_code, 200)
        self.assertEqual(len(expense.attachment_ids), 2)
        self.assertEqual(expense.message_main_attachment_id.name, 'manager.txt')

        manager_attachment = expense.attachment_ids.filtered(lambda a: a.create_uid == standard_user_manager)
        manager_attachment.with_user(standard_user_manager).unlink()
        self.assertEqual(len(expense.attachment_ids), 1)

        # The admin should be able to upload and delete an attachment on the expense.
        admin_response = upload_receipt(admin_user, 'admin.txt', b"Admin\n")
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(len(expense.attachment_ids), 2)
        self.assertEqual(expense.message_main_attachment_id.name, 'admin.txt')

        admin_attachment = expense.attachment_ids.filtered(lambda a: a.create_uid == admin_user)
        admin_attachment.with_user(admin_user).unlink()
        self.assertEqual(len(expense.attachment_ids), 1)

        expense.with_user(standard_user_manager).action_approve()

        # Once the expense is approved, nobody should be able to upload or delete an attachment on the expense except someone with sudo.
        with self.assertRaises(UserError):
            expense.with_user(standard_user).attachment_ids.unlink()
        user_response_after_approval = upload_receipt(standard_user, 'salut2.txt', b"Salut 2 !\n")
        self.assertEqual(user_response_after_approval.status_code, 200)
        self.assertTrue(user_response_after_approval.json()['error']['message'])
        self.assertEqual(len(expense.attachment_ids), 1)  # No new attachment

        with self.assertRaises(UserError):
            expense.with_user(standard_user_manager).attachment_ids.unlink()
        manager_response_after_approval = upload_receipt(standard_user_manager, 'manager2.txt', b"Manager 2\n")
        self.assertEqual(manager_response_after_approval.status_code, 200)
        self.assertTrue(manager_response_after_approval.json()['error']['message'])
        self.assertEqual(len(expense.attachment_ids), 1)  # No new attachment

        admin_response_after_approval = upload_receipt(admin_user, 'admin2.txt', b"Admin 2\n")
        self.assertEqual(admin_response_after_approval.status_code, 200)
        self.assertTrue(admin_response_after_approval.json()['error']['message'])
        self.assertEqual(len(expense.attachment_ids), 1)  # No new attachment

        # If really needed, sudo should always be able to delete the attachments
        user_attachment = expense.attachment_ids.filtered(lambda a: a.create_uid == standard_user)
        self.assertEqual(len(user_attachment), 1)
        user_attachment.sudo().unlink()
        self.assertEqual(len(expense.attachment_ids), 0)

    def test_expense_filter(self):
        """ Tests '_search_filter_for_expense' domain filtering per user role.
            - Expense Manager: Sees all employees across the company.
            - Team Approver: Sees only themselves and their direct reports.
            - Base Employee: Sees only their own employee record.
        """
        hr_admin_user = new_test_user(self.env, login='hr_admin_user', groups='base.group_user,hr.group_hr_user')
        Employee = self.env['hr.employee'].with_user(hr_admin_user)
        approver_user = new_test_user(self.env, login='approver_user', groups='base.group_user,hr_expense.group_hr_expense_team_approver')
        approver_employee = Employee.create({'name': 'approver_emp', 'user_id': approver_user.id})
        subordinate_employee = Employee.create({'name': 'subordinate_emp', 'parent_id': approver_employee.id})

        base_user = new_test_user(self.env, login='base_user', groups='base.group_user')
        base_employee = Employee.create({'name': 'base_emp', 'user_id': base_user.id})

        test_cases = [
            ('Expense Manager', self.expense_user_manager, self.expense_employee + base_employee + approver_employee + subordinate_employee),
            ('Team Approver', approver_user, approver_employee + subordinate_employee),
            ('Base Employee', base_user, base_employee),
        ]

        for case_name, user, expected_employees in test_cases:
            with self.subTest(case_name=case_name):
                employees = self.env['hr.employee'].with_user(user).search([('filter_for_expense', '=', True)])
                self.assertEqual(employees, expected_employees)
