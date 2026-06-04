# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged('-at_install', 'post_install')
class TestExpensesAccessRights(TestExpenseCommon, HttpCase):

    def test_expense_access_rights(self):
        """ The expense employee can't be able to create an expense for someone else. """

        expense_employee_2 = self.env['hr.employee'].create({
            'name': 'expense_employee_2',
            'user_id': self.env.user.id,
            'work_contact_id': self.env.user.partner_id.id,
        })

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
        expense_employee = self.env['hr.employee'].create({
            'name': 'expense_employee_base_user',
            'user_id': user.id,
            'work_contact_id': user.partner_id.id,
            'expense_manager_id': self.expense_user_manager.id,
            'address_id': user.partner_id.id,
        })

        expense = self.env['hr.expense'].with_user(user).create({
            'name': 'First Expense for employee',
            'employee_id': expense_employee.id,
            # Expense without foreign currency but analytic account.
            'product_id': self.product_a.id,
            'price_unit': 1000.0,
        })
        self.start_tour("/odoo", 'hr_expense_access_rights_test_tour', login="test-expense")
        self.assertRecordValues(expense, [{'state': 'submitted'}])

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

        # When testing for uploading the attachments, we can't simulate it through a tour as using inputFiles isn't possible
        # with a AttachDocumentWidget since the input isn't added to the DOM.

        # User that created the expense should be able to upload an attachment on the expense.
        # But he shouldn't be able to delete it once it's submitted
        self.authenticate(standard_user.login, standard_user.login)
        user_response = self.url_open(
            "/web/binary/upload_attachment",
            {
                'csrf_token': http.Request.csrf_token(self),
                'id': expense.id,
                'model': 'hr.expense',
            },
            files={'ufile': ('salut.txt', b"Salut !\n", 'text/plain')},
        )
        expense.with_user(standard_user).attach_document(attachment_ids=[attachment['id'] for attachment in user_response.json()])
        self.assertEqual(user_response.status_code, 200)
        self.assertEqual(len(expense.attachment_ids), 1)
        self.assertEqual(expense.message_main_attachment_id.id, user_response.json()[0]['id'])

        with self.assertRaises(UserError):
            expense.with_user(standard_user).attachment_ids.unlink()

        # User without any access to the expense shouldn't be able to upload an attachment on the expense.
        self.authenticate(another_standard_user.login, another_standard_user.login)
        with mute_logger('odoo.addons.web.controllers.binary'):  # To avoid logging the AccessError raised when trying to upload the attachment.
            response = self.url_open(
                "/web/binary/upload_attachment",
                {
                    'csrf_token': http.Request.csrf_token(self),
                    'id': expense.id,
                    'model': 'hr.expense',
                },
                files={'ufile': ('fail.txt', b"Fail\n", 'text/plain')},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['error'], 'You are not allowed to upload an attachment here.')
        self.assertEqual(len(expense.attachment_ids), 1)  # No new attachment
        self.assertEqual(expense.message_main_attachment_id.id, user_response.json()[0]['id'])

        # The manager should be able to upload and delete an attachment on the expense.
        self.authenticate(standard_user_manager.login, standard_user_manager.login)
        manager_response = self.url_open(
            "/web/binary/upload_attachment",
            {
                'csrf_token': http.Request.csrf_token(self),
                'id': expense.id,
                'model': 'hr.expense',
            },
            files={'ufile': ('manager.txt', b"Manager\n", 'text/plain')},
        )
        expense.with_user(standard_user_manager).attach_document(attachment_ids=[attachment['id'] for attachment in manager_response.json()])
        self.assertEqual(manager_response.status_code, 200)
        self.assertEqual(len(expense.attachment_ids), 2)
        self.assertEqual(expense.message_main_attachment_id.id, manager_response.json()[0]['id'])

        manager_attachment = expense.attachment_ids.filtered(lambda a: a.create_uid == standard_user_manager)
        manager_attachment.with_user(standard_user_manager).unlink()
        self.assertEqual(len(expense.attachment_ids), 1)

        # The admin should be able to upload and delete an attachment on the expense.
        self.authenticate(admin_user.login, admin_user.login)
        admin_response = self.url_open(
            "/web/binary/upload_attachment",
            {
                'csrf_token': http.Request.csrf_token(self),
                'id': expense.id,
                'model': 'hr.expense',
            },
            files={'ufile': ('admin.txt', b"Admin\n", 'text/plain')},
        )
        expense.with_user(admin_user).attach_document(attachment_ids=[attachment['id'] for attachment in admin_response.json()])
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(len(expense.attachment_ids), 2)
        self.assertEqual(expense.message_main_attachment_id.id, admin_response.json()[0]['id'])

        admin_attachment = expense.attachment_ids.filtered(lambda a: a.create_uid == admin_user)
        admin_attachment.with_user(admin_user).unlink()
        self.assertEqual(len(expense.attachment_ids), 1)

        expense.with_user(standard_user_manager).action_approve()

        # Once the expense is approved, nobody should be able to upload or delete an attachment on the expense except someone with sudo.
        self.authenticate(standard_user.login, standard_user.login)
        with self.assertRaises(UserError):
            expense.with_user(standard_user).attachment_ids.unlink()
        with mute_logger('odoo.addons.web.controllers.binary'):  # To avoid logging the AccessError raised when trying to upload the attachment.
            user_response_after_approval = self.url_open(
                "/web/binary/upload_attachment",
                {
                    'csrf_token': http.Request.csrf_token(self),
                    'id': expense.id,
                    'model': 'hr.expense',
                },
                files={'ufile': ('salut2.txt', b"Salut 2 !\n", 'text/plain')},
            )
        self.assertEqual(user_response_after_approval.status_code, 200)
        self.assertEqual(user_response_after_approval.json()[0]['error'], 'You are not allowed to upload an attachment here.')
        self.assertEqual(len(expense.attachment_ids), 1)  # No new attachment

        self.authenticate(standard_user_manager.login, standard_user_manager.login)
        with self.assertRaises(UserError):
            expense.with_user(standard_user_manager).attachment_ids.unlink()
        with mute_logger('odoo.addons.web.controllers.binary'):  # To avoid logging the AccessError raised when trying to upload the attachment.
            manager_response_after_approval = self.url_open(
                "/web/binary/upload_attachment",
                {
                    'csrf_token': http.Request.csrf_token(self),
                    'id': expense.id,
                    'model': 'hr.expense',
                },
                files={'ufile': ('manager2.txt', b"Manager 2\n", 'text/plain')},
            )
        self.assertEqual(manager_response_after_approval.status_code, 200)
        self.assertEqual(manager_response_after_approval.json()[0]['error'], 'You are not allowed to upload an attachment here.')
        self.assertEqual(len(expense.attachment_ids), 1)  # No new attachment

        self.authenticate(admin_user.login, admin_user.login)
        with mute_logger('odoo.addons.web.controllers.binary'):  # To avoid logging the AccessError raised when trying to upload the attachment.
            admin_response_after_approval = self.url_open(
                "/web/binary/upload_attachment",
                {
                    'csrf_token': http.Request.csrf_token(self),
                    'id': expense.id,
                    'model': 'hr.expense',
                },
                files={'ufile': ('admin2.txt', b"Admin 2\n", 'text/plain')},
            )
        self.assertEqual(admin_response_after_approval.status_code, 200)
        self.assertEqual(admin_response_after_approval.json()[0]['error'], 'You are not allowed to upload an attachment here.')
        self.assertEqual(len(expense.attachment_ids), 1)  # No new attachment

        # If really needed, sudo should always be able to delete the attachments
        user_attachment = expense.attachment_ids.filtered(lambda a: a.create_uid == standard_user)
        self.assertEqual(len(user_attachment), 1)
        user_attachment.sudo().unlink()
        self.assertEqual(len(expense.attachment_ids), 0)
