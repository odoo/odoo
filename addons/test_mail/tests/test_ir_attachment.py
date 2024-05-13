from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError


class TestAttachment(MailCommon):

    def test_attachment_forbid_unlink(self):
        """Check that removing message attachments is prevented on other user's messages."""
        test_record = self.env['mail.test.simple'].with_context(self._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        })

        user_second_employee = mail_new_test_user(
            self.env,
            login="employee_second",
            email="employee_second@example.com",
            groups="base.group_user",
        )

        admin_attachments = self.env['ir.attachment'].with_user(self.user_admin).create([{
            'type': 'binary',
            'name': f'admin_attachment_{n}',
            'datas': "ABC=",
        } for n in range(2)])
        employee_attachments = self.env['ir.attachment'].with_user(self.user_employee).create([{
            'type': 'binary',
            'name': f'employee_attachment_{n}',
            'datas': "ABC=",
        } for n in range(2)])

        second_employee_attachment = self.env['ir.attachment'].with_user(user_second_employee).create({
            'type': 'binary',
            'name': 'second_employee_attachment',
            'datas': "ABC=",
        })

        # used in different messages by different users
        shared_attachment_employee = self.env['ir.attachment'].with_user(self.user_employee).create({
            'res_model': test_record._name,
            'res_id': test_record.id,
            'type': 'binary',
            'name': 'shared_attachment_employee',
            'datas': "ABC=",
        })

        test_record.with_user(self.user_admin).message_post(body="Hi", attachment_ids=admin_attachments.ids)
        test_record.with_user(self.user_employee).message_post(body="Hello", attachment_ids=(employee_attachments + shared_attachment_employee).ids)
        test_record.with_user(user_second_employee).message_post(body="Hello again", attachment_ids=shared_attachment_employee.ids)
        test_record.with_user(user_second_employee).message_post(body="Hello again with own attachment", attachment_ids=second_employee_attachment.ids)

        # forbidden
        forbidden_list = [
            (self.user_employee, admin_attachments[0]),
            (self.user_employee, second_employee_attachment),
            (user_second_employee, shared_attachment_employee),
        ]
        for user, attachment in forbidden_list:
            with self.subTest(user=user.name, attachment=attachment.name, method='write'):
                with self.assertRaises(AccessError):
                    attachment.with_user(user).write({'datas': '0123'})
            with self.subTest(user=user.name, attachment=attachment.name, method='unlink'):
                with self.assertRaises(AccessError):
                    attachment.with_user(user).unlink()

        # allowed
        allowed_list = [
            (self.user_admin, admin_attachments[0], False),
            (self.user_admin, employee_attachments[0], False),
            (self.user_employee, admin_attachments[1], True),  # can happen when using access tokens
            (self.user_employee, employee_attachments[1], False),
            (self.user_employee, shared_attachment_employee, False),  # original creator may always delete it, for performance reasons
        ]
        for user, attachment, sudo in allowed_list:
            with self.subTest(user=user.name, attachment=attachment.name, sudo=sudo, method='write'):
                attachment.with_user(user).sudo(sudo).write({'datas': '1234'})
                self.assertEqual(attachment.datas, b'1234')
            with self.subTest(user=user.name, attachment=attachment.name, sudo=sudo, method='unlink'):
                attachment.with_user(user).sudo(sudo).unlink()
                self.assertFalse(attachment.exists())

        shared_attachment_employee.with_user(user_second_employee).write({'name': 'Successful write to shared attachment'})
        self.assertEqual(shared_attachment_employee.name, 'Successful write to shared attachment', 'Only data fields should be protected')
