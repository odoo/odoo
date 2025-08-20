from contextlib import contextmanager
from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged, users

from odoo.addons.base.models.ir_mail_server import IrMail_Server
from odoo.exceptions import UserError, ValidationError


@tagged('mail_server')
class TestIrMailServerPersonal(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('mail.disable_personal_mail_servers', False)
        cls.user_admin.email = 'admin@test.lan'
        cls.user_employee.email = 'employee@test.lan'
        cls.user_employee.group_ids += cls.env.ref('mass_mailing.group_mass_mailing_user')
        cls.test_partner = cls.env['res.partner'].create({
            'name': 'test partner', 'email': 'test.partner@test.lan'
        })
        cls.mail_server_user.write({
            'from_filter': cls.user_employee.email,
            'owner_user_id': cls.user_employee,
            'smtp_user': cls.user_employee.email,
        })
        cls.user_employee.invalidate_recordset(['outgoing_mail_server_id'])

    @contextmanager
    def mock_mail_connect(self):
        original_connect = IrMail_Server._connect__
        self.connected_server_ids = []

        def patched_connect(mail_server, *args, **kwargs):
            self.connected_server_ids.append(kwargs.get('mail_server_id'))
            original_connect(mail_server, *args, **kwargs)

        with patch.object(IrMail_Server, '_connect__', autospec=True, wraps=IrMail_Server, side_effect=patched_connect):
            yield

    @users('admin', 'employee')
    def test_personal_mail_server_allowed_post(self):
        """Check that only the owner of the mail server can create mails that will be sent from it."""
        test_record = self.test_partner.with_user(self.env.user)
        with self.mock_mail_connect():
            test_record.message_post(
                body='hello',
                author_id=self.user_employee.partner_id.id, email_from=self.user_employee.email,
                partner_ids=test_record.ids,
            )

        self.assertEqual(len(self.connected_server_ids), 1)
        if self.env.user == self.mail_server_user.owner_user_id:
            self.assertEqual(self.connected_server_ids[0], self.mail_server_user.id)
        else:
            self.assertNotEqual(self.connected_server_ids[0], self.mail_server_user.id)

        # check disallowed exceptions
        if self.env.user != self.mail_server_user.owner_user_id:
            # check raise on invalid server at create
            with self.assertRaises(ValidationError):
                test_record.message_post(
                    body='hello',
                    author_id=self.user_employee.partner_id.id, email_from=self.user_employee.email,
                    mail_server_id=self.mail_server_user.id,
                    partner_ids=test_record.ids,
                )

            # check raise on invalid server at send (should not happen in normal flow)
            mail = self.env['mail.mail'].sudo().create({
                'body_html': 'hello',
                'email_from': self.user_employee.email,
                'author_id': self.user_employee.partner_id.id,
                'partner_ids': test_record.ids,
            })
            with self.mock_mail_gateway(), self.assertRaisesRegex(UserError, "Unauthorized server for some of the sending mails."):
                mail._send(self, mail_server=self.mail_server_user)

    def test_personal_mail_server_find_mail_server(self):
        """Check that _find_mail_server only finds 'public' servers unless otherwise allowed."""
        IrMailServer = self.env['ir.mail_server']
        all_servers = IrMailServer.search([])
        test_cases = [
            (None, False),
            (all_servers, True),
        ]
        for mail_servers, should_find_personal in test_cases:
            with self.subTest(mail_servers=mail_servers):
                found_server, found_email_from = IrMailServer._find_mail_server(self.user_employee.email, mail_servers=mail_servers)
                if should_find_personal:
                    self.assertEqual(
                        (found_server, found_email_from), (self.mail_server_user, self.user_employee.email),
                        'Passing in a server that is owned should allow finding it.'
                    )
                else:
                    self.assertNotEqual(
                        found_server, self.mail_server_user,
                        'Finding a server for an email_from without specifying a list of servers should not find owned servers.'
                    )

    @users('employee')
    def test_immutable_create_uid(self):
        """Make sure create_uid is not writable, as it's a security assumption for these tests."""
        message = self.test_partner.with_user(self.env.user).message_post(
            body='hello',
            author_id=self.user_employee.partner_id.id, email_from=self.user_employee.email,
            partner_ids=self.test_partner.ids,
        )

        self.assertEqual(message.create_uid, self.user_employee)
        message.create_uid = self.user_admin
        self.assertEqual(message.create_uid, self.user_employee)

    def test_personal_mail_server_mail_for_existing_message(self):
        """Crons should be able to send a mail from a personal server for an existing message."""
        message = self.test_partner.with_user(self.user_employee).message_post(body='hello')
        message.partner_ids += self.test_partner
        with self.mock_mail_connect():
            self.test_partner.with_user(self.env.ref('base.user_root'))._notify_thread(message)
        self.assertEqual(self.connected_server_ids, [self.mail_server_user.id], "Should have used message creator's server.")
