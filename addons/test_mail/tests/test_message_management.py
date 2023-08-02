# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('mail_wizards')
class TestMailResend(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailResend, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        #Two users
        cls.user1 = mail_new_test_user(cls.env, login='e1', groups='base.group_user', name='Employee 1', notification_type='email', email='e1')  # invalid email
        cls.user2 = mail_new_test_user(cls.env, login='e2', groups='base.group_portal', name='Employee 2', notification_type='email', email='e2@example.com')
        #Two partner
        cls.partner1 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Partner 1',
            'email': 'p1'  # invalid email
        })
        cls.partner2 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Partner 2',
            'email': 'p2@example.com'
        })
        cls.partners = cls.env['res.partner'].concat(cls.user1.partner_id, cls.user2.partner_id, cls.partner1, cls.partner2)
        cls.invalid_email_partners = cls.env['res.partner'].concat(cls.user1.partner_id, cls.partner1)

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_resend_workflow(self):
        with self.assertSinglePostNotifications(
                [{'partner': partner, 'type': 'email', 'status': 'exception'} for partner in self.partners],
                message_info={'message_type': 'notification'}):
            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        self.assertEqual(wizard.notification_ids.mapped('res_partner_id'), self.partners, "wizard should manage notifications for each failed partner")

        # three more failure sent on bus, one for each mail in failure and one for resend
        self._reset_bus()
        expected_bus_notifications = [
            (self.cr.dbname, 'res.partner', self.partner_admin.id),
            (self.cr.dbname, 'res.partner', self.env.user.partner_id.id),
        ]
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications * 3):
            wizard.resend_mail_action()
        done_msgs, done_notifs = self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'exception' if partner in self.user1.partner_id | self.partner1 else 'sent'} for partner in self.partners]}]
        )
        self.assertEqual(wizard.notification_ids, done_notifs)
        self.assertEqual(done_msgs, message)

        self.user1.write({"email": 'u1@example.com'})

        # two more failure update sent on bus, one for failed mail and one for resend
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications * 2):
            self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        done_msgs, done_notifs = self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'exception' if partner == self.partner1 else 'sent', 'check_send': partner == self.partner1} for partner in self.partners]}]
        )
        self.assertEqual(wizard.notification_ids, done_notifs)
        self.assertEqual(done_msgs, message)

        self.partner1.write({"email": 'p1@example.com'})

        # A success update should be sent on bus once the email has no more failure
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications):
            self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'sent', 'check_send': partner == self.partner1} for partner in self.partners]}]
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_remove_mail_become_canceled(self):
        # two failure sent on bus, one for each mail
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)] * 2):
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'exception' if partner in self.user1.partner_id | self.partner1 else 'sent'} for partner in self.partners]}]
        )

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        partners = wizard.contact_ids.mapped("partner_id")
        self.assertEqual(self.invalid_email_partners, partners)
        wizard.contact_ids.filtered(lambda p: p.partner_id == self.partner1).write({"resend": False})
        wizard.resend_mail_action()

        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email',
                        'status': (partner == self.user1.partner_id and 'exception') or (partner == self.partner1 and 'canceled') or 'sent'} for partner in self.partners]}]
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_cancel_all(self):
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)] * 2):
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        # one update for cancell
        self._reset_bus()
        expected_bus_notifications = [
            (self.cr.dbname, 'res.partner', self.partner_admin.id),
            (self.cr.dbname, 'res.partner', self.env.user.partner_id.id),
        ]
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications):
            wizard.cancel_mail_action()

        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email',
                        'check_send': partner in self.user1.partner_id | self.partner1,
                        'status': 'canceled' if partner in self.user1.partner_id | self.partner1 else 'sent'} for partner in self.partners]}]
        )


@tagged('mail_wizards')
class TestMailResendNoPartner(MailCommon):
    @classmethod
    def setUpClass(cls):
        super(TestMailResendNoPartner, cls).setUpClass()
        cls.valid_email = 'valid@test.lan'
        # individual invalid emails are currently not handled in the composer (either silently removed or bounced depending format)
        cls.valid_email2 = 'valid2@test.lan'
        cls.unpartnered_emails = set([cls.valid_email, cls.valid_email2])
        cls.test_record = cls.env['mail.test.ticket'].with_context(cls._test_context).create([
            {'email_from': ','.join(cls.unpartnered_emails),
             'name': 'Test Valid Email',
             }
        ])
        # composer without partners required to generate unpartnered_email notifications
        cls.composer = cls.env['mail.compose.message'].with_user(cls.user_admin).create({
            'author_id': cls.partner_admin.id,
            'body': '<p>Test Body</p>',
            'composition_mode': 'mass_mail',
            'email_from': cls.user_admin.email_formatted,
            'message_type': 'notification',
            'model': cls.test_record._name,
            'res_ids': cls.test_record.ids,
            'subject': 'My amazing subject',
        })

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('admin')
    def test_mail_resend_workflow_email(self):
        with self.assertSinglePostNotifications(
                [{'unpartnered_email': email, 'type': 'email', 'status': 'exception'} for email in self.unpartnered_emails],
                message_info={'content': 'Test Body', 'message_type': 'email', 'subtype': self.env['mail.message.subtype']}):

            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect

            mails_sudo, _ = self.composer.with_user(self.env.user)._action_send_mail()

        message = mails_sudo.mail_message_id
        self.assertEqual(len(message), 1)
        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        self.assertEqual(set(wizard.notification_ids.mapped('unpartnered_email')), self.unpartnered_emails, "wizard should manage notifications for each failed partner")

        # check notified of resend
        self._reset_bus()
        expected_bus_notifications = [
            (self.cr.dbname, 'res.partner', self.partner_admin.id),
        ]
        # resend without server error and update email
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications):
            new_valid_email = 'valid3@example.lan'
            wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
            wizard.contact_ids.filtered(lambda contact: contact.email == self.valid_email2).write({"email": new_valid_email})
            wizard.resend_mail_action()

        done_msgs, done_notifs = self.assertMailNotifications(message, [
            {'content': 'Test Body', 'message_type': 'email', 'subtype': self.env['mail.message.subtype'],
             'notif': [{'unpartnered_email': email, 'type': 'email', 'status': 'sent'} for email in [new_valid_email, self.valid_email]]}]
        )
        self.assertEqual(wizard.notification_ids, done_notifs)
        self.assertEqual(done_msgs, message)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('admin')
    def test_cancel_half_email(self):
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)]):
            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect

            mails_sudo, _ = self.composer.with_user(self.env.user)._action_send_mail()
        message = mails_sudo.mail_message_id

        self.assertMailNotifications(message, [
            {'content': 'Test Body', 'message_type': 'email', 'subtype': self.env['mail.message.subtype'],
             'notif': [{'unpartnered_email': email, 'type': 'email', 'status': 'exception'} for email in self.unpartnered_emails]}]
        )

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        email_addrs = set(wizard.contact_ids.mapped("email"))
        self.assertEqual(self.unpartnered_emails, email_addrs)
        wizard.contact_ids.filtered(lambda c: c.email == self.valid_email2).write({"resend": False})
        with self.mock_mail_gateway():
            wizard.resend_mail_action()

        self.assertMailNotifications(message, [
            {'content': 'Test Body', 'message_type': 'email', 'subtype': self.env['mail.message.subtype'],
             'notif': [{'unpartnered_email': email, 'type': 'email',
                        'status': (email == self.valid_email and 'sent') or (email == self.valid_email2 and 'canceled') or 'sent'} for email in self.unpartnered_emails]}]
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @users('admin')
    def test_cancel_all_email(self):
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)]):
            def _connect(*args, **kwargs):
                raise Exception("Some exception")
            self.connect_mocked.side_effect = _connect

            mails_sudo, _ = self.composer.with_user(self.env.user)._action_send_mail()
        message = mails_sudo.mail_message_id

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})

        self._reset_bus()
        expected_bus_notifications = [
            (self.cr.dbname, 'res.partner', self.partner_admin.id),
        ]
        with self.mock_mail_gateway(), self.assertBus(expected_bus_notifications):
            wizard.cancel_mail_action()

        self.assertMailNotifications(message, [
            {'content': 'Test Body', 'message_type': 'email', 'subtype': self.env['mail.message.subtype'],
             'notif': [{'unpartnered_email': email, 'type': 'email',
                        'check_send': True,
                        'status': 'canceled'} for email in self.unpartnered_emails]}]
        )
