# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2
import pytz
import smtplib

from datetime import datetime, timedelta
from freezegun import freeze_time
from OpenSSL.SSL import Error as SSLError
from socket import gaierror, timeout
from unittest.mock import call

from odoo import api, tools
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.test_mail.tests.common import TestMailCommon
from odoo.tests import common, tagged
from odoo.tools import mute_logger, DEFAULT_SERVER_DATETIME_FORMAT


@tagged('mail_mail')
class TestMailMail(TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailMail, cls).setUpClass()
        cls._init_mail_servers()

        cls.server_domain_2 = cls.env['ir.mail_server'].create({
            'name': 'Server 2',
            'smtp_host': 'test_2.com',
            'from_filter': 'test_2.com',
        })

        cls.test_record = cls.env['mail.test.gateway'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        }).with_context({})

        cls.test_message = cls.test_record.message_post(body='<p>Message</p>', subject='Subject')
        cls.test_mail = cls.env['mail.mail'].create([{
            'body': '<p>Body</p>',
            'email_from': False,
            'email_to': 'test@example.com',
            'is_notification': True,
            'subject': 'Subject',
        }])
        cls.test_notification = cls.env['mail.notification'].create({
            'is_read': False,
            'mail_mail_id': cls.test_mail.id,
            'mail_message_id': cls.test_message.id,
            'notification_type': 'email',
            'res_partner_id': cls.partner_employee.id,  # not really used for matching except multi-recipients
        })

        cls.emails_falsy = [False, '', ' ']
        cls.emails_invalid = ['buggy', 'buggy, wrong']
        cls.emails_invalid_ascii = ['raoul@example¢¡.com']
        cls.emails_valid = ['raoul¢¡@example.com', 'raoul@example.com']

    def _reset_data(self):
        self._init_mail_mock()
        self.test_mail.write({'failure_reason': False, 'failure_type': False, 'state': 'outgoing'})
        self.test_notification.write({'failure_type': False, 'notification_status': 'ready'})


    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_recipients(self):
        """ Partner_ids is a field used from mail_message, but not from mail_mail. """
        mail = self.env['mail.mail'].sudo().create({
            'body_html': '<p>Test</p>',
            'email_to': 'test@example.com',
            'partner_ids': [(4, self.user_employee.partner_id.id)]
        })
        with self.mock_mail_gateway():
            mail.send()
        self.assertSentEmail(mail.env.user.partner_id, ['test@example.com'])
        self.assertEqual(len(self._mails), 1)

        mail = self.env['mail.mail'].sudo().create({
            'body_html': '<p>Test</p>',
            'email_to': 'test@example.com',
            'recipient_ids': [(4, self.user_employee.partner_id.id)],
        })
        with self.mock_mail_gateway():
            mail.send()
        self.assertSentEmail(mail.env.user.partner_id, ['test@example.com'])
        self.assertSentEmail(mail.env.user.partner_id, [self.user_employee.email_formatted])
        self.assertEqual(len(self._mails), 2)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_return_path(self):
        # mail without thread-enabled record
        base_values = {
            'body_html': '<p>Test</p>',
            'email_to': 'test@example.com',
        }

        mail = self.env['mail.mail'].create(base_values)
        with self.mock_mail_gateway():
            mail.send()
        self.assertEqual(self._mails[0]['headers']['Return-Path'], '%s@%s' % (self.alias_bounce, self.alias_domain))

        # mail on thread-enabled record
        mail = self.env['mail.mail'].create(dict(base_values, **{
            'model': self.test_record._name,
            'res_id': self.test_record.id,
        }))
        with self.mock_mail_gateway():
            mail.send()
        self.assertEqual(self._mails[0]['headers']['Return-Path'], '%s@%s' % (self.alias_bounce, self.alias_domain))

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_mail_mail_schedule(self):
        """Test that a mail scheduled in the past/future are sent or not"""
        now = datetime(2022, 6, 28, 14, 0, 0)
        scheduled_datetimes = [
            # falsy values
            False, '', 'This is not a date format',
            # datetimes (UTC/GMT +10 hours for Australia/Brisbane)
            now, pytz.timezone('Australia/Brisbane').localize(now),
            # string
            (now - timedelta(days=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            (now + timedelta(days=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            (now + timedelta(days=1)).strftime("%H:%M:%S %d-%m-%Y"),
            # tz: is actually 1 hour before now in UTC
            (now + timedelta(hours=3)).strftime("%H:%M:%S %d-%m-%Y") + " +0400",
            # tz: is actually 1 hour after now in UTC
            (now + timedelta(hours=-3)).strftime("%H:%M:%S %d-%m-%Y") + " -0400",
        ]
        expected_datetimes = [
            False, '', False,
            now, now - pytz.timezone('Australia/Brisbane').utcoffset(now),
            now - timedelta(days=1), now + timedelta(days=1), now + timedelta(days=1),
            now + timedelta(hours=-1),
            now + timedelta(hours=1),
        ]
        expected_states = [
            # falsy values = send now
            'sent', 'sent', 'sent',
            'sent', 'sent',
            'sent', 'outgoing', 'outgoing',
            'sent', 'outgoing'
        ]

        mails = self.env['mail.mail'].create([
            {'body_html': '<p>Test</p>',
             'email_to': 'test@example.com',
             'scheduled_date': scheduled_datetime,
            } for scheduled_datetime in scheduled_datetimes
        ])

        for mail, expected_datetime, scheduled_datetime in zip(mails, expected_datetimes, scheduled_datetimes):
            expected = expected_datetime.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT) if expected_datetime else expected_datetime
            self.assertEqual(mail.scheduled_date, expected,
                             'Scheduled date: %s should be stored as %s, received %s' % (scheduled_datetime, expected, mail.scheduled_date))
            self.assertEqual(mail.state, 'outgoing')

        with freeze_time(now):
            self.env['mail.mail'].process_email_queue()
            for mail, expected_state in zip(mails, expected_states):
                self.assertEqual(mail.state, expected_state)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_send_exceptions_origin(self):
        """ Test various use case with exceptions and errors and see how they are
        managed and stored at mail and notification level. """
        mail, notification = self.test_mail, self.test_notification

        # MailServer.build_email(): invalid from
        self.env['ir.config_parameter'].set_param('mail.default.from', '')
        self._reset_data()
        with self.mock_mail_gateway(), mute_logger('odoo.addons.mail.models.mail_mail'):
            mail.send(raise_exception=False)
        self.assertFalse(self._mails[0]['email_from'])
        self.assertIn(
            'You must either provide a sender address explicitly or configure using the combination of `mail.catchall.domain` and `mail.default.from` ICPs',
            mail.failure_reason)
        self.assertFalse(mail.failure_type, 'Mail: void from: no failure type, should be updated')
        self.assertEqual(mail.state, 'exception')
        self.assertEqual(notification.failure_type, 'unknown', 'Mail: void from: unknown failure type, should be updated')
        self.assertEqual(notification.notification_status, 'exception')

        # MailServer.send_email(): _prepare_email_message: unexpected ASCII
        # Force catchall domain to void otherwise bounce is set to postmaster-odoo@domain
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', '')
        self._reset_data()
        mail.write({'email_from': 'strange@example¢¡.com'})
        with self.mock_mail_gateway():
            mail.send(raise_exception=False)
        self.assertEqual(self._mails[0]['email_from'], 'strange@example¢¡.com')
        self.assertIn('Codepoint U+00A2 at position', mail.failure_reason)
        self.assertFalse(mail.failure_type, 'Mail: bugged from (ascii): no failure type, should be updated')
        self.assertEqual(mail.state, 'exception')
        self.assertEqual(notification.failure_type, 'unknown', 'Mail: bugged from (ascii): unknown failure type, should be updated')
        self.assertEqual(notification.notification_status, 'exception')

        # MailServer.send_email(): _prepare_email_message: unexpected ASCII based on catchall domain
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'domain¢¡.com')
        self._reset_data()
        mail.write({'email_from': 'test.user@example.com'})
        with self.mock_mail_gateway():
            mail.send(raise_exception=False)
        self.assertEqual(self._mails[0]['email_from'], 'test.user@example.com')
        self.assertIn('Codepoint U+00A2 at position', mail.failure_reason)
        self.assertFalse(mail.failure_type, 'Mail: bugged catchall domain (ascii): no failure type, should be updated')
        self.assertEqual(mail.state, 'exception')
        self.assertEqual(notification.failure_type, 'unknown', 'Mail: bugged catchall domain (ascii): unknown failure type, should be updated')
        self.assertEqual(notification.notification_status, 'exception')

        # MailServer.send_email(): _prepare_email_message: Malformed 'Return-Path' or 'From' address
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', '')
        self._reset_data()
        mail.write({'email_from': 'robert'})
        with self.mock_mail_gateway():
            mail.send(raise_exception=False)
        self.assertEqual(self._mails[0]['email_from'], 'robert')
        self.assertIn("Malformed 'Return-Path' or 'From' address: robert", mail.failure_reason)
        self.assertFalse(mail.failure_type, 'Mail: bugged from (ascii): no failure type, should be updated')
        self.assertEqual(mail.state, 'exception')
        self.assertEqual(notification.failure_type, 'unknown', 'Mail: bugged from (ascii): unknown failure type, should be updated')
        self.assertEqual(notification.notification_status, 'exception')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_send_exceptions_recipients_emails(self):
        """ Test various use case with exceptions and errors and see how they are
        managed and stored at mail and notification level. """
        mail, notification = self.test_mail, self.test_notification

        self.env['ir.config_parameter'].set_param('mail.catchall.domain', self.alias_domain)
        self.env['ir.config_parameter'].set_param('mail.default.from', self.default_from)

        # MailServer.send_email(): _prepare_email_message: missing To
        for email_to in self.emails_falsy:
            self._reset_data()
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertIn('Error without exception. Probably due do sending an email without computed recipients.', mail.failure_reason)
            self.assertFalse(mail.failure_type, 'Mail: missing email_to: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            if email_to == ' ':
                self.assertEqual(notification.failure_type, 'mail_email_missing')
                self.assertEqual(notification.notification_status, 'exception')
            else:
                self.assertEqual(notification.failure_type, False, 'Mail: missing email_to: notification is wrongly set as sent')
                self.assertEqual(notification.notification_status, 'sent', 'Mail: missing email_to: notification is wrongly set as sent')

        # MailServer.send_email(): _prepare_email_message: invalid To
        for email_to, failure_type in zip(self.emails_invalid,
                                          ['mail_email_missing', 'mail_email_missing']):
            self._reset_data()
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertIn('Error without exception. Probably due do sending an email without computed recipients.', mail.failure_reason)
            self.assertFalse(mail.failure_type, 'Mail: invalid email_to: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(notification.failure_type, failure_type, 'Mail: invalid email_to: missing instead of invalid')
            self.assertEqual(notification.notification_status, 'exception')

        # MailServer.send_email(): _prepare_email_message: invalid To (ascii)
        for email_to in self.emails_invalid_ascii:
            self._reset_data()
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertIn('Codepoint U+00A2 at position', mail.failure_reason)
            self.assertFalse(mail.failure_type, 'Mail: invalid (ascii) recipient partner: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(notification.failure_type, 'unknown', 'Mail: invalid (ascii) recipient partner: unknown failure type, should be updated')
            self.assertEqual(notification.notification_status, 'exception')

        # MailServer.send_email(): _prepare_email_message: ok To (ascii or just ok)
        for email_to in self.emails_valid:
            self._reset_data()
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertFalse(mail.failure_reason)
            self.assertFalse(mail.failure_type)
            self.assertEqual(mail.state, 'sent')
            self.assertFalse(notification.failure_type)
            self.assertEqual(notification.notification_status, 'sent')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_send_exceptions_recipients_partners(self):
        """ Test various use case with exceptions and errors and see how they are
        managed and stored at mail and notification level. """
        mail, notification = self.test_mail, self.test_notification

        mail.write({'email_from': 'test.user@test.example.com', 'email_to': False})
        partners_falsy = self.env['res.partner'].create([
            {'name': 'Name %s' % email, 'email': email}
            for email in self.emails_falsy
        ])
        partners_invalid = self.env['res.partner'].create([
            {'name': 'Name %s' % email, 'email': email}
            for email in self.emails_invalid
        ])
        partners_invalid_ascii = self.env['res.partner'].create([
            {'name': 'Name %s' % email, 'email': email}
            for email in self.emails_invalid_ascii
        ])
        partners_valid = self.env['res.partner'].create([
            {'name': 'Name %s' % email, 'email': email}
            for email in self.emails_valid
        ])

        # void values
        for partner in partners_falsy:
            self._reset_data()
            mail.write({'recipient_ids': [(5, 0), (4, partner.id)]})
            notification.write({'res_partner_id': partner.id})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertEqual(mail.failure_reason, 'Error without exception. Probably due do sending an email without computed recipients.')
            self.assertFalse(mail.failure_type, 'Mail: void recipient partner: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(notification.failure_type, 'mail_email_invalid', 'Mail: void recipient partner: should be missing, not invalid')
            self.assertEqual(notification.notification_status, 'exception')

        # wrong values
        for partner in partners_invalid:
            self._reset_data()
            mail.write({'recipient_ids': [(5, 0), (4, partner.id)]})
            notification.write({'res_partner_id': partner.id})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertEqual(mail.failure_reason, 'Error without exception. Probably due do sending an email without computed recipients.')
            self.assertFalse(mail.failure_type, 'Mail: invalid recipient partner: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(notification.failure_type, 'mail_email_invalid')
            self.assertEqual(notification.notification_status, 'exception')

        # ascii ko
        for partner in partners_invalid_ascii:
            self._reset_data()
            mail.write({'recipient_ids': [(5, 0), (4, partner.id)]})
            notification.write({'res_partner_id': partner.id})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertIn('Codepoint U+00A2 at position', mail.failure_reason)
            self.assertFalse(mail.failure_type, 'Mail: invalid (ascii) recipient partner: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(notification.failure_type, 'unknown', 'Mail: invalid (ascii) recipient partner: unknown failure type, should be updated')
            self.assertEqual(notification.notification_status, 'exception')

        # ascii ok or just ok
        for partner in partners_valid:
            self._reset_data()
            mail.write({'recipient_ids': [(5, 0), (4, partner.id)]})
            notification.write({'res_partner_id': partner.id})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertFalse(mail.failure_reason)
            self.assertFalse(mail.failure_type)
            self.assertEqual(mail.state, 'sent')
            self.assertFalse(notification.failure_type)
            self.assertEqual(notification.notification_status, 'sent')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_send_exceptions_recipients_partners_mixed(self):
        """ Test various use case with exceptions and errors and see how they are
        managed and stored at mail and notification level. """
        mail, notification = self.test_mail, self.test_notification

        mail.write({'email_to': 'test@example.com'})
        partners_falsy = self.env['res.partner'].create([
            {'name': 'Name %s' % email, 'email': email}
            for email in self.emails_falsy
        ])
        partners_invalid = self.env['res.partner'].create([
            {'name': 'Name %s' % email, 'email': email}
            for email in self.emails_invalid
        ])
        partners_valid = self.env['res.partner'].create([
            {'name': 'Name %s' % email, 'email': email}
            for email in self.emails_valid
        ])

        # valid to, missing email for recipient or wrong email for recipient
        for partner in partners_falsy + partners_invalid:
            self._reset_data()
            mail.write({'recipient_ids': [(5, 0), (4, partner.id)]})
            notification.write({'res_partner_id': partner.id})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertFalse(mail.failure_reason, 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertFalse(mail.failure_type, 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertEqual(mail.state, 'sent', 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertEqual(notification.failure_type, 'mail_email_invalid', 'Mail: void email considered as invalid')
            self.assertEqual(notification.notification_status, 'exception')

        # update to have valid partner and invalid partner
        mail.write({'recipient_ids': [(5, 0), (4, partners_valid[1].id), (4, partners_falsy[0].id)]})
        notification.write({'res_partner_id': partners_valid[1].id})
        notification2 = notification.create({
            'is_read': False,
            'mail_mail_id': mail.id,
            'mail_message_id': self.test_message.id,
            'notification_type': 'email',
            'res_partner_id': partners_falsy[0].id,
        })

        # missing to / invalid to
        for email_to in self.emails_falsy + self.emails_invalid:
            self._reset_data()
            notification2.write({'failure_type': False, 'notification_status': 'ready'})
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertFalse(mail.failure_reason, 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertFalse(mail.failure_type, 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertEqual(mail.state, 'sent', 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertFalse(notification.failure_type)
            self.assertEqual(notification.notification_status, 'sent')
            self.assertEqual(notification2.failure_type, 'mail_email_invalid')
            self.assertEqual(notification2.notification_status, 'exception')

        # buggy to (ascii)
        for email_to in self.emails_invalid_ascii:
            self._reset_data()
            notification2.write({'failure_type': False, 'notification_status': 'ready'})
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertIn('Codepoint U+00A2 at position', mail.failure_reason)
            self.assertFalse(mail.failure_type, 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(notification.failure_type, 'unknown')
            self.assertEqual(notification.notification_status, 'exception')
            self.assertEqual(notification2.failure_type, 'unknown')
            self.assertEqual(notification2.notification_status, 'exception')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_send_exceptions_raise_management(self):
        """ Test various use case with exceptions and errors and see how they are
        managed and stored at mail and notification level. """
        mail, notification = self.test_mail, self.test_notification
        mail.write({'email_from': 'test.user@test.example.com', 'email_to': 'test@example.com'})

        # SMTP connecting issues
        with self.mock_mail_gateway():
            _connect_current = self.connect_mocked.side_effect

            # classic errors that may be raised during sending, just to test their current support
            for error, msg in [
                    (smtplib.SMTPServerDisconnected('SMTPServerDisconnected'), 'SMTPServerDisconnected'),
                    (smtplib.SMTPResponseException('code', 'SMTPResponseException'), 'code\nSMTPResponseException'),
                    (smtplib.SMTPNotSupportedError('SMTPNotSupportedError'), 'SMTPNotSupportedError'),
                    (smtplib.SMTPException('SMTPException'), 'SMTPException'),
                    (SSLError('SSLError'), 'SSLError'),
                    (gaierror('gaierror'), 'gaierror'),
                    (timeout('timeout'), 'timeout')]:

                def _connect(*args, **kwargs):
                    raise error
                self.connect_mocked.side_effect = _connect

                mail.send(raise_exception=False)
                self.assertFalse(mail.failure_type)
                self.assertEqual(mail.failure_reason, msg)
                self.assertEqual(mail.state, 'exception')
                self.assertEqual(notification.failure_type, 'mail_smtp')
                self.assertEqual(notification.notification_status, 'exception')
                self._reset_data()

        self.connect_mocked.side_effect = _connect_current

        # SMTP sending issues
        with self.mock_mail_gateway():
            _send_current = self.send_email_mocked.side_effect
            self._reset_data()
            mail.write({'email_to': 'test@example.com'})

            # should always raise for those errors, even with raise_exception=False
            for error, error_class in [
                    (smtplib.SMTPServerDisconnected("Some exception"), smtplib.SMTPServerDisconnected),
                    (MemoryError("Some exception"), MemoryError)]:
                def _send_email(*args, **kwargs):
                    raise error
                self.send_email_mocked.side_effect = _send_email

                with self.assertRaises(error_class):
                    mail.send(raise_exception=False)
                self.assertFalse(mail.failure_reason, 'SMTPServerDisconnected/MemoryError during Send raises and lead to a rollback')
                self.assertFalse(mail.failure_type, 'SMTPServerDisconnected/MemoryError during Send raises and lead to a rollback')
                self.assertEqual(mail.state, 'outgoing', 'SMTPServerDisconnected/MemoryError during Send raises and lead to a rollback')
                self.assertFalse(notification.failure_type, 'SMTPServerDisconnected/MemoryError during Send raises and lead to a rollback')
                self.assertEqual(notification.notification_status, 'ready', 'SMTPServerDisconnected/MemoryError during Send raises and lead to a rollback')

            # MailDeliveryException: should be catched; other issues are sub-catched under
            # a MailDeliveryException and are catched
            for error, msg in [
                    (MailDeliveryException("Some exception"), 'Some exception'),
                    (ValueError("Unexpected issue"), 'Unexpected issue')]:
                def _send_email(*args, **kwargs):
                    raise error
                self.send_email_mocked.side_effect = _send_email

                self._reset_data()
                mail.send(raise_exception=False)
                self.assertEqual(mail.failure_reason, msg)
                self.assertFalse(mail.failure_type, 'Mail: unlogged failure type to fix')
                self.assertEqual(mail.state, 'exception')
                self.assertEqual(notification.failure_type, 'unknown', 'Mail: generic failure type')
                self.assertEqual(notification.notification_status, 'exception')

            self.send_email_mocked.side_effect = _send_current

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_send_server(self):
        """Test that the mails are send in batch.

        Batch are defined by the mail server and the email from field.
        """
        self.assertEqual(self.env['ir.mail_server']._get_default_from_address(), 'notifications@test.com')

        mail_values = {
            'body_html': '<p>Test</p>',
            'email_to': 'user@example.com',
        }

        # Should be encapsulated in the notification email
        mails = self.env['mail.mail'].create([{
            **mail_values,
            'email_from': 'test@unknown_domain.com',
        } for _ in range(5)]) | self.env['mail.mail'].create([{
            **mail_values,
            'email_from': 'test_2@unknown_domain.com',
        } for _ in range(5)])

        # Should use the test_2 mail server
        # Once with "user_1@test_2.com" as login
        # Once with "user_2@test_2.com" as login
        mails |= self.env['mail.mail'].create([{
            **mail_values,
            'email_from': 'user_1@test_2.com',
        } for _ in range(5)]) | self.env['mail.mail'].create([{
            **mail_values,
            'email_from': 'user_2@test_2.com',
        } for _ in range(5)])

        # Mail server is forced
        mails |= self.env['mail.mail'].create([{
            **mail_values,
            'email_from': 'user_1@test_2.com',
            'mail_server_id': self.server_domain.id,
        } for _ in range(5)])

        with self.mock_smtplib_connection():
            mails.send()

        self.assertEqual(self.find_mail_server_mocked.call_count, 4, 'Must be called only once per "mail from" when the mail server is not forced')
        self.assertEqual(len(self.emails), 25)

        # Check call to the connect method to ensure that we authenticate
        # to the right mail server with the right login
        self.assertEqual(self.connect_mocked.call_count, 4, 'Must be called once per batch which share the same mail server and the same smtp from')
        self.connect_mocked.assert_has_calls(
            calls=[
                call(smtp_from='notifications@test.com', mail_server_id=self.server_notification.id),
                call(smtp_from='user_1@test_2.com', mail_server_id=self.server_domain_2.id),
                call(smtp_from='user_2@test_2.com', mail_server_id=self.server_domain_2.id),
                call(smtp_from='user_1@test_2.com', mail_server_id=self.server_domain.id),
            ],
            any_order=True,
        )

        self.assert_email_sent_smtp(message_from='"test" <notifications@test.com>',
                                    emails_count=5, from_filter=self.server_notification.from_filter)
        self.assert_email_sent_smtp(message_from='"test_2" <notifications@test.com>',
                                    emails_count=5, from_filter=self.server_notification.from_filter)
        self.assert_email_sent_smtp(message_from='user_1@test_2.com', emails_count=5, from_filter=self.server_domain_2.from_filter)
        self.assert_email_sent_smtp(message_from='user_2@test_2.com', emails_count=5, from_filter=self.server_domain_2.from_filter)
        self.assert_email_sent_smtp(message_from='user_1@test_2.com', emails_count=5, from_filter=self.server_domain.from_filter)


@tagged('mail_mail')
class TestMailMailRace(common.TransactionCase):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_bounce_during_send(self):
        self.partner = self.env['res.partner'].create({
            'name': 'Ernest Partner',
        })
        # we need to simulate a mail sent by the cron task, first create mail, message and notification by hand
        mail = self.env['mail.mail'].sudo().create({
            'body_html': '<p>Test</p>',
            'is_notification': True,
            'state': 'outgoing',
            'recipient_ids': [(4, self.partner.id)]
        })
        mail_message = mail.mail_message_id

        message = self.env['mail.message'].create({
            'subject': 'S',
            'body': 'B',
            'subtype_id': self.ref('mail.mt_comment'),
            'notification_ids': [(0, 0, {
                'res_partner_id': self.partner.id,
                'mail_mail_id': mail.id,
                'notification_type': 'email',
                'is_read': True,
                'notification_status': 'ready',
            })],
        })
        notif = self.env['mail.notification'].search([('res_partner_id', '=', self.partner.id)])
        # we need to commit transaction or cr will keep the lock on notif
        self.cr.commit()

        # patch send_email in order to create a concurent update and check the notif is already locked by _send()
        this = self  # coding in javascript ruinned my life
        bounce_deferred = []
        @api.model
        def send_email(self, message, *args, **kwargs):
            with this.registry.cursor() as cr, mute_logger('odoo.sql_db'):
                try:
                    # try ro aquire lock (no wait) on notification (should fail)
                    cr.execute("SELECT notification_status FROM mail_notification WHERE id = %s FOR UPDATE NOWAIT", [notif.id])
                except psycopg2.OperationalError:
                    # record already locked by send, all good
                    bounce_deferred.append(True)
                else:
                    # this should trigger psycopg2.extensions.TransactionRollbackError in send().
                    # Only here to simulate the initial use case
                    # If the record is lock, this line would create a deadlock since we are in the same thread
                    # In practice, the update will wait the end of the send() transaction and set the notif as bounce, as expeced
                    cr.execute("UPDATE mail_notification SET notification_status='bounce' WHERE id = %s", [notif.id])
            return message['Message-Id']
        self.env['ir.mail_server']._patch_method('send_email', send_email)

        mail.send()

        self.assertTrue(bounce_deferred, "The bounce should have been deferred")
        self.assertEqual(notif.notification_status, 'sent')

        # some cleaning since we commited the cr
        self.env['ir.mail_server']._revert_method('send_email')

        notif.unlink()
        mail.unlink()
        (mail_message | message).unlink()
        self.partner.unlink()
        self.env.cr.commit()

        # because we committed the cursor, the savepoint of the test method is
        # gone, and this would break TransactionCase cleanups
        self.cr.execute('SAVEPOINT test_%d' % self._savepoint_id)
