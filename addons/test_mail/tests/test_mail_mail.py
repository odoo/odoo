# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2
import pytz
import re
import smtplib
from email import message_from_string

from datetime import datetime, timedelta
from freezegun import freeze_time
from markupsafe import Markup
from OpenSSL.SSL import Error as SSLError
from socket import gaierror, timeout
from unittest.mock import call, patch, PropertyMock

from odoo import api, Command, fields, SUPERUSER_ID
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError
from odoo.tests import common, tagged, users
from odoo.tools import formataddr, mute_logger


@tagged('mail_mail')
class TestMailMail(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailMail, cls).setUpClass()

        cls.test_record = cls.env['mail.test.gateway'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        }).with_context({})

        cls.test_message = cls.test_record.message_post(body=Markup('<p>Message</p>'), subject='Subject')
        cls.test_mail = cls.env['mail.mail'].create([{
            'body': Markup('<p>Body</p>'),
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
        self.test_notification.write({'failure_reason': False, 'failure_type': False, 'notification_status': 'ready'})

    @users('admin')
    def test_mail_mail_attachment_access(self):
        mail = self.env['mail.mail'].create({
            'body_html': 'Test',
            'email_to': 'test@example.com',
            'partner_ids': [(4, self.user_employee.partner_id.id)],
            'attachment_ids': [
                (0, 0, {'name': 'file 1', 'datas': 'c2VjcmV0'}),
                (0, 0, {'name': 'file 2', 'datas': 'c2VjcmV0'}),
                (0, 0, {'name': 'file 3', 'datas': 'c2VjcmV0'}),
                (0, 0, {'name': 'file 4', 'datas': 'c2VjcmV0'}),
            ],
        })

        def _patched_check(self, *args, **kwargs):
            if self.env.is_superuser():
                return
            if any(attachment.name in ('file 2', 'file 4') for attachment in self):
                raise AccessError('No access')

        mail.invalidate_recordset()

        new_attachment = self.env['ir.attachment'].create({
            'name': 'new file',
            'datas': 'c2VjcmV0',
        })

        with patch.object(type(self.env['ir.attachment']), 'check', _patched_check):
            # Sanity check
            self.assertEqual(mail.restricted_attachment_count, 2)
            self.assertEqual(len(mail.unrestricted_attachment_ids), 2)
            self.assertEqual(mail.unrestricted_attachment_ids.mapped('name'), ['file 1', 'file 3'])

            # Add a new attachment
            mail.write({
                'unrestricted_attachment_ids': [Command.link(new_attachment.id)],
            })
            self.assertEqual(mail.restricted_attachment_count, 2)
            self.assertEqual(len(mail.unrestricted_attachment_ids), 3)
            self.assertEqual(mail.unrestricted_attachment_ids.mapped('name'), ['file 1', 'file 3', 'new file'])
            self.assertEqual(len(mail.attachment_ids), 5)

            # Remove an attachment
            mail.write({
                'unrestricted_attachment_ids': [Command.unlink(new_attachment.id)],
            })
            self.assertEqual(mail.restricted_attachment_count, 2)
            self.assertEqual(len(mail.unrestricted_attachment_ids), 2)
            self.assertEqual(mail.unrestricted_attachment_ids.mapped('name'), ['file 1', 'file 3'])
            self.assertEqual(len(mail.attachment_ids), 4)

            # Reset command
            mail.invalidate_recordset()
            mail.write({'unrestricted_attachment_ids': [Command.clear()]})
            self.assertEqual(len(mail.unrestricted_attachment_ids), 0)
            self.assertEqual(len(mail.attachment_ids), 2)

            # Read in SUDO
            mail.invalidate_recordset()
            self.assertEqual(mail.sudo().restricted_attachment_count, 2)
            self.assertEqual(len(mail.sudo().unrestricted_attachment_ids), 0)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_headers(self):
        """ Test headers management when set on outgoing mail. """
        # mail without thread-enabled record
        base_values = {
            'body_html': '<p>Test</p>',
            'email_to': 'test@example.com',
            'headers': {'foo': 'bar'},
        }

        for headers, expected in [
            ({'foo': 'bar'}, {'foo': 'bar'}),
            ("{'foo': 'bar'}", {'foo': 'bar'}),
            ("{'foo': 'bar', 'baz': '3+2'}", {'foo': 'bar', 'baz': '3+2'}),
            (['not_a_dict'], {}),
            ('alsonotadict', {}),
            ("['not_a_dict']", {}),
            ("{'invaliddict'}", {}),
        ]:
            with self.subTest(headers=headers, expected=expected):
                mail = self.env['mail.mail'].create([
                    dict(base_values, headers=headers)
                ])
                with self.mock_mail_gateway():
                    mail.send()
                for key, value in expected.items():
                    self.assertIn(key, self._mails[0]['headers'])
                    self.assertEqual(self._mails[0]['headers'][key], value)

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
    def test_mail_mail_recipients_cc(self):
        """ Partner_ids is a field used from mail_message, but not from mail_mail. """
        mail = self.env['mail.mail'].sudo().create({
            'body_html': '<p>Test</p>',
            'email_cc': 'test.cc.1@example.com, "Herbert" <test.cc.2@example.com>',
            'email_to': 'test.rec.1@example.com, "Raoul" <test.rec.2@example.com>',
            'recipient_ids': [(4, self.user_employee.partner_id.id)],
        })

        with self.mock_mail_gateway():
            mail.send()
        # note that formatting is lost for cc
        self.assertSentEmail(mail.env.user.partner_id,
                             ['test.rec.1@example.com', '"Raoul" <test.rec.2@example.com>'],
                             email_cc=['test.cc.1@example.com', 'test.cc.2@example.com'])
        # don't put CCs as copy of each outgoing email, only the first one (and never
        # with partner based recipients as those may receive specific links)
        self.assertSentEmail(mail.env.user.partner_id, [self.user_employee.email_formatted],
                             email_cc=[])
        self.assertEqual(len(self._mails), 2)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_recipients_formatting(self):
        """ Check support of email / formatted email """
        mail = self.env['mail.mail'].sudo().create({
            'author_id': False,
            'body_html': '<p>Test</p>',
            'email_cc': 'test.cc.1@example.com, "Herbert" <test.cc.2@example.com>',
            'email_from': '"Ignasse" <test.from@example.com>',
            'email_to': 'test.rec.1@example.com, "Raoul" <test.rec.2@example.com>',
        })

        with self.mock_mail_gateway():
            mail.send()
        # note that formatting is lost for cc
        self.assertSentEmail('"Ignasse" <test.from@example.com>',
                             ['test.rec.1@example.com', '"Raoul" <test.rec.2@example.com>'],
                             email_cc=['test.cc.1@example.com', 'test.cc.2@example.com'])
        self.assertEqual(len(self._mails), 1)

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
            fields.Datetime.to_string(now - timedelta(days=1)),
            fields.Datetime.to_string(now + timedelta(days=1)),
            (now + timedelta(days=1)).strftime("%H:%M:%S %d-%m-%Y"),
            # tz: is actually 1 hour before now in UTC
            (now + timedelta(hours=3)).strftime("%H:%M:%S %d-%m-%Y") + " +0400",
            # tz: is actually 1 hour after now in UTC
            (now + timedelta(hours=-3)).strftime("%H:%M:%S %d-%m-%Y") + " -0400",
        ]
        expected_datetimes = [
            False, False, False,
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
            self.assertEqual(mail.scheduled_date, expected_datetime,
                             'Scheduled date: %s should be stored as %s, received %s' % (scheduled_datetime, expected_datetime, mail.scheduled_date))
            self.assertEqual(mail.state, 'outgoing')

        with freeze_time(now):
            self.env['mail.mail'].process_email_queue()
            for mail, expected_state in zip(mails, expected_states):
                self.assertEqual(mail.state, expected_state)

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.tests')
    def test_mail_mail_send_configuration(self):
        """ Test configuration and control of email queue """
        self.env['mail.mail'].search([]).unlink()  # cleanup queue

        # test 'mail.mail.queue.batch.size': cron fetch size
        for queue_batch_size, exp_send_count in [
            (3, 3),
            (0, 10),  # maximum available
            (False, 10),  # maximum available
        ]:
            with self.subTest(queue_batch_size=queue_batch_size), \
                 self.mock_mail_gateway():
                self.env['ir.config_parameter'].sudo().set_param('mail.mail.queue.batch.size', queue_batch_size)
                mails = self.env['mail.mail'].create([
                    {
                        'auto_delete': False,
                        'body_html': f'Batch Email {idx}',
                        'email_from': 'test.from@mycompany.example.com',
                        'email_to': 'test.outgoing@test.example.com',
                        'state': 'outgoing',
                    }
                    for idx in range(10)
                ])

                self.env['mail.mail'].process_email_queue()
                self.assertEqual(len(self._mails), exp_send_count)
                mails.write({'state': 'sent'})  # avoid conflicts between batch

        # test 'mail.session.batch.size': batch send size
        self.env['ir.config_parameter'].sudo().set_param('mail.mail.queue.batch.size', False)
        for session_batch_size, exp_call_count in [
            (3, 4),  # 10 mails -> 4 iterations of 3
            (0, 1),
            (False, 1),
        ]:
            with self.subTest(session_batch_size=session_batch_size), \
                 self.mock_mail_gateway():
                self.env['ir.config_parameter'].sudo().set_param('mail.session.batch.size', session_batch_size)
                mails = self.env['mail.mail'].create([
                    {
                        'auto_delete': False,
                        'body_html': f'Batch Email {idx}',
                        'email_from': 'test.from@mycompany.example.com',
                        'email_to': 'test.outgoing@test.example.com',
                        'state': 'outgoing',
                    }
                    for idx in range(10)
                ])

                self.env['mail.mail'].process_email_queue()
                self.assertEqual(self.mail_mail_private_send_mocked.call_count, exp_call_count)
                mails.write({'state': 'sent'})  # avoid conflicts between batch

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_send_exceptions_origin(self):
        """ Test various use case with exceptions and errors and see how they are
        managed and stored at mail and notification level. """
        mail, notification = self.test_mail, self.test_notification

        # MailServer.build_email(): invalid from (missing)
        for default_from in [False, '']:
            self.mail_alias_domain.default_from = default_from
            self._reset_data()
            with self.mock_mail_gateway(), mute_logger('odoo.addons.mail.models.mail_mail'):
                mail.send(raise_exception=False)
            self.assertFalse(self._mails[0]['email_from'])
            self.assertEqual(
                mail.failure_reason,
                'You must either provide a sender address explicitly or configure using the combination of `mail.catchall.domain` and `mail.default.from` ICPs, in the server configuration file or with the --email-from startup parameter.')
            self.assertEqual(mail.failure_type, 'mail_from_missing')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(
                notification.failure_reason,
                'You must either provide a sender address explicitly or configure using the combination of `mail.catchall.domain` and `mail.default.from` ICPs, in the server configuration file or with the --email-from startup parameter.')
            self.assertEqual(notification.failure_type, 'mail_from_missing')
            self.assertEqual(notification.notification_status, 'exception')

        # MailServer.send_email(): _prepare_email_message: unexpected ASCII / Malformed 'Return-Path' or 'From' address
        # Force bounce alias to void, will force usage of email_from
        self.mail_alias_domain.bounce_alias = False
        self.env.company.invalidate_recordset(fnames={'bounce_email', 'bounce_formatted'})
        for email_from in ['strange@example¢¡.com', 'robert']:
            self._reset_data()
            mail.write({'email_from': email_from})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertEqual(self._mails[0]['email_from'], email_from)
            self.assertEqual(mail.failure_reason, f"Malformed 'Return-Path' or 'From' address: {email_from} - It should contain one valid plain ASCII email")
            self.assertEqual(mail.failure_type, 'mail_from_invalid')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(notification.failure_reason, f"Malformed 'Return-Path' or 'From' address: {email_from} - It should contain one valid plain ASCII email")
            self.assertEqual(notification.failure_type, 'mail_from_invalid')
            self.assertEqual(notification.notification_status, 'exception')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_send_exceptions_recipients_emails(self):
        """ Test various use case with exceptions and errors and see how they are
        managed and stored at mail and notification level. """
        mail, notification = self.test_mail, self.test_notification

        # MailServer.send_email(): _prepare_email_message: missing To
        for email_to in self.emails_falsy:
            self._reset_data()
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertEqual(mail.failure_reason, 'Error without exception. Probably due to sending an email without computed recipients.')
            self.assertFalse(mail.failure_type, 'Mail: missing email_to: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            if email_to == ' ':
                self.assertFalse(notification.failure_reason, 'Mail: failure reason not propagated')
                self.assertEqual(notification.failure_type, 'mail_email_missing')
                self.assertEqual(notification.notification_status, 'exception')
            else:
                self.assertFalse(notification.failure_reason, 'Mail: failure reason not propagated')
                self.assertEqual(notification.failure_type, False, 'Mail: missing email_to: notification is wrongly set as sent')
                self.assertEqual(notification.notification_status, 'sent', 'Mail: missing email_to: notification is wrongly set as sent')

        # MailServer.send_email(): _prepare_email_message: invalid To
        for email_to, failure_type in zip(
            self.emails_invalid,
            ['mail_email_missing', 'mail_email_missing']
        ):
            self._reset_data()
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertEqual(mail.failure_reason, 'Error without exception. Probably due to sending an email without computed recipients.')
            self.assertFalse(mail.failure_type, 'Mail: invalid email_to: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertFalse(notification.failure_reason, 'Mail: failure reason not propagated')
            self.assertEqual(notification.failure_type, failure_type, 'Mail: invalid email_to: missing instead of invalid')
            self.assertEqual(notification.notification_status, 'exception')

        # MailServer.send_email(): _prepare_email_message: invalid To (ascii)
        for email_to in self.emails_invalid_ascii:
            self._reset_data()
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertEqual(mail.failure_reason, 'Error without exception. Probably due to sending an email without computed recipients.')
            self.assertFalse(mail.failure_type, 'Mail: invalid (ascii) recipient partner: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(notification.failure_type, 'mail_email_invalid')
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
            self.assertFalse(notification.failure_reason)
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
            self.assertEqual(mail.failure_reason, 'Error without exception. Probably due to sending an email without computed recipients.')
            self.assertFalse(mail.failure_type, 'Mail: void recipient partner: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertFalse(notification.failure_reason, 'Mail: failure reason not propagated')
            self.assertEqual(notification.failure_type, 'mail_email_invalid', 'Mail: void recipient partner: should be missing, not invalid')
            self.assertEqual(notification.notification_status, 'exception')

        # wrong values
        for partner in partners_invalid:
            self._reset_data()
            mail.write({'recipient_ids': [(5, 0), (4, partner.id)]})
            notification.write({'res_partner_id': partner.id})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertEqual(mail.failure_reason, 'Error without exception. Probably due to sending an email without computed recipients.')
            self.assertFalse(mail.failure_type, 'Mail: invalid recipient partner: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertFalse(notification.failure_reason, 'Mail: failure reason not propagated')
            self.assertEqual(notification.failure_type, 'mail_email_invalid')
            self.assertEqual(notification.notification_status, 'exception')

        # ascii ko
        for partner in partners_invalid_ascii:
            self._reset_data()
            mail.write({'recipient_ids': [(5, 0), (4, partner.id)]})
            notification.write({'res_partner_id': partner.id})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertEqual(mail.failure_reason, 'Error without exception. Probably due to sending an email without computed recipients.')
            self.assertFalse(mail.failure_type, 'Mail: invalid (ascii) recipient partner: no failure type, should be updated')
            self.assertEqual(mail.state, 'exception')
            self.assertEqual(notification.failure_type, 'mail_email_invalid')
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
            self.assertFalse(notification.failure_reason)
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
            self.assertFalse(notification.failure_reason, 'Mail: void email considered as invalid')
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
            notification2.write({'failure_reason': False, 'failure_type': False, 'notification_status': 'ready'})
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)
            self.assertFalse(mail.failure_reason, 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertFalse(mail.failure_type, 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertEqual(mail.state, 'sent', 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertFalse(notification.failure_reason)
            self.assertFalse(notification.failure_type)
            self.assertEqual(notification.notification_status, 'sent')
            self.assertFalse(notification2.failure_reason)
            self.assertEqual(notification2.failure_type, 'mail_email_invalid')
            self.assertEqual(notification2.notification_status, 'exception')

        # buggy to (ascii)
        for email_to in self.emails_invalid_ascii:
            self._reset_data()
            notification2.write({'failure_reason': False, 'failure_type': False, 'notification_status': 'ready'})
            mail.write({'email_to': email_to})
            with self.mock_mail_gateway():
                mail.send(raise_exception=False)

            self.assertFalse(mail.failure_type, 'Mail: at least one valid recipient, mail is sent to avoid send loops and spam')
            self.assertEqual(mail.state, 'sent')
            self.assertFalse(notification.failure_type)
            self.assertEqual(notification.notification_status, 'sent')
            self.assertEqual(notification2.failure_type, 'mail_email_invalid')
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
                self.assertEqual(mail.failure_reason, msg)
                self.assertFalse(mail.failure_type)
                self.assertEqual(mail.state, 'exception')
                self.assertFalse(notification.failure_reason, 'Mail: failure reason not propagated')
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
                self.assertFalse(notification.failure_reason, 'SMTPServerDisconnected/MemoryError during Send raises and lead to a rollback')
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
                self.assertEqual(mail.failure_type, 'unknown', 'Mail: unlogged failure type to fix')
                self.assertEqual(mail.state, 'exception')
                self.assertEqual(notification.failure_reason, msg)
                self.assertEqual(notification.failure_type, 'unknown', 'Mail: generic failure type')
                self.assertEqual(notification.notification_status, 'exception')

            self.send_email_mocked.side_effect = _send_current

    def test_mail_mail_values_misc(self):
        """ Test various values on mail.mail, notably default values """
        msg = self.env['mail.mail'].create({})
        self.assertEqual(msg.message_type, 'email_outgoing', 'Mails should have outgoing email type by default')

@tagged('mail_mail', 'mail_server')
class TestMailMailServer(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.mail_server_domain_2 = cls.env['ir.mail_server'].create({
            'from_filter': 'test_2.com',
            'name': 'Server 2',
            'smtp_host': 'test_2.com',
        })
        cls.test_record = cls.env['mail.test.gateway'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        }).with_context({})

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_send_server(self):
        """Test that the mails are send in batch.

        Batch are defined by the mail server and the email from field.
        """
        self.assertEqual(
            self.env['ir.mail_server']._get_default_from_address(),
            f'{self.default_from}@{self.alias_domain}'
        )

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
        mails += self.env['mail.mail'].create([{
            **mail_values,
            'email_from': 'user_1@test_2.com',
        } for _ in range(5)]) + self.env['mail.mail'].create([{
            **mail_values,
            'email_from': 'user_2@test_2.com',
        } for _ in range(5)])

        # Mail server is forced
        mails += self.env['mail.mail'].create([{
            **mail_values,
            'email_from': 'user_1@test_2.com',
            'mail_server_id': self.mail_server_domain.id,
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
                call(smtp_from=f'{self.default_from}@{self.alias_domain}', mail_server_id=self.mail_server_notification.id),
                call(smtp_from='user_1@test_2.com', mail_server_id=self.mail_server_domain_2.id),
                call(smtp_from='user_2@test_2.com', mail_server_id=self.mail_server_domain_2.id),
                call(smtp_from='user_1@test_2.com', mail_server_id=self.mail_server_domain.id),
            ],
            any_order=True,
        )

        self.assertSMTPEmailsSent(message_from=f'"test" <{self.default_from}@{self.alias_domain}>',
                                  emails_count=5, from_filter=self.mail_server_notification.from_filter)
        self.assertSMTPEmailsSent(message_from=f'"test_2" <{self.default_from}@{self.alias_domain}>',
                                  emails_count=5, from_filter=self.mail_server_notification.from_filter)
        self.assertSMTPEmailsSent(message_from='user_1@test_2.com', emails_count=5, mail_server=self.mail_server_domain_2)
        self.assertSMTPEmailsSent(message_from='user_2@test_2.com', emails_count=5, mail_server=self.mail_server_domain_2)
        self.assertSMTPEmailsSent(message_from='user_1@test_2.com', emails_count=5, mail_server=self.mail_server_domain)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_values_email_formatted(self):
        """ Test outgoing email values, with formatting """
        customer = self.env['res.partner'].create({
            'name': 'Tony Customer',
            'email': '"Formatted Emails" <tony.customer@test.example.com>',
        })
        mail = self.env['mail.mail'].create({
            'body_html': '<p>Test</p>',
            'email_cc': '"Ignasse, le Poilu" <test.cc.1@test.example.com>',
            'email_to': '"Raoul, le Grand" <test.email.1@test.example.com>, "Micheline, l\'immense" <test.email.2@test.example.com>',
            'recipient_ids': [(4, self.user_employee.partner_id.id), (4, customer.id)]
        })
        with self.mock_mail_gateway():
            mail.send()
        self.assertEqual(len(self._mails), 3, 'Mail: sent 3 emails: 1 for email_to, 1 / recipient')
        self.assertEqual(
            sorted(sorted(_mail['email_to']) for _mail in self._mails),
            sorted([sorted(['"Raoul, le Grand" <test.email.1@test.example.com>', '"Micheline, l\'immense" <test.email.2@test.example.com>']),
                    [formataddr((self.user_employee.name, self.user_employee.email_normalized))],
                    [formataddr(("Tony Customer", 'tony.customer@test.example.com'))]
                   ]),
            'Mail: formatting issues should have been removed as much as possible'
        )
        # CC are added to first email
        self.assertEqual(
            [_mail['email_cc'] for _mail in self._mails],
            [['test.cc.1@test.example.com'], [], []],
            'Mail: currently always removing formatting in email_cc'
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_values_email_multi(self):
        """ Test outgoing email values, with email field holding multi emails """
        # Multi
        customer = self.env['res.partner'].create({
            'name': 'Tony Customer',
            'email': 'tony.customer@test.example.com, norbert.customer@test.example.com',
        })
        mail = self.env['mail.mail'].create({
            'body_html': '<p>Test</p>',
            'email_cc': 'test.cc.1@test.example.com, test.cc.2@test.example.com',
            'email_to': 'test.email.1@test.example.com, test.email.2@test.example.com',
            'recipient_ids': [(4, self.user_employee.partner_id.id), (4, customer.id)]
        })
        with self.mock_mail_gateway():
            mail.send()
        self.assertEqual(len(self._mails), 3, 'Mail: sent 3 emails: 1 for email_to, 1 / recipient')
        self.assertEqual(
            sorted(sorted(_mail['email_to']) for _mail in self._mails),
            sorted([sorted(['test.email.1@test.example.com', 'test.email.2@test.example.com']),
                   [formataddr((self.user_employee.name, self.user_employee.email_normalized))],
                    sorted([formataddr(("Tony Customer", 'tony.customer@test.example.com')),
                            formataddr(("Tony Customer", 'norbert.customer@test.example.com'))]),
                   ]),
            'Mail: formatting issues should have been removed as much as possible (multi emails in a single address are managed '
            'like separate emails when sending with recipient_ids'
        )
        # CC are added to first email
        self.assertEqual(
            [_mail['email_cc'] for _mail in self._mails],
            [['test.cc.1@test.example.com', 'test.cc.2@test.example.com'], [], []],
        )

        # Multi + formatting
        customer = self.env['res.partner'].create({
            'name': 'Tony Customer',
            'email': 'tony.customer@test.example.com, "Norbert Customer" <norbert.customer@test.example.com>',
        })
        mail = self.env['mail.mail'].create({
            'body_html': '<p>Test</p>',
            'email_cc': 'test.cc.1@test.example.com, test.cc.2@test.example.com',
            'email_to': 'test.email.1@test.example.com, test.email.2@test.example.com',
            'recipient_ids': [(4, self.user_employee.partner_id.id), (4, customer.id)]
        })
        with self.mock_mail_gateway():
            mail.send()
        self.assertEqual(len(self._mails), 3, 'Mail: sent 3 emails: 1 for email_to, 1 / recipient')
        self.assertEqual(
            sorted(sorted(_mail['email_to']) for _mail in self._mails),
            sorted([sorted(['test.email.1@test.example.com', 'test.email.2@test.example.com']),
                   [formataddr((self.user_employee.name, self.user_employee.email_normalized))],
                    sorted([formataddr(("Tony Customer", 'tony.customer@test.example.com')),
                            formataddr(("Tony Customer", 'norbert.customer@test.example.com'))]),
                   ]),
            'Mail: formatting issues should have been removed as much as possible (multi emails in a single address are managed '
            'like separate emails when sending with recipient_ids (and partner name is always used as name part)'
        )
        # CC are added to first email
        self.assertEqual(
            [_mail['email_cc'] for _mail in self._mails],
            [['test.cc.1@test.example.com', 'test.cc.2@test.example.com'], [], []],
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_mail_values_unicode(self):
        """ Unicode should be fine. """
        mail = self.env['mail.mail'].create({
            'body_html': '<p>Test</p>',
            'email_cc': 'test.😊.cc@example.com',
            'email_to': 'test.😊@example.com',
        })
        with self.mock_mail_gateway():
            mail.send()
        self.assertEqual(len(self._mails), 1)
        self.assertEqual(self._mails[0]['email_cc'], ['test.😊.cc@example.com'])
        self.assertEqual(self._mails[0]['email_to'], ['test.😊@example.com'])

    @mute_logger('odoo.addons.mail.models.mail_mail')
    @patch('odoo.addons.base.models.ir_attachment.IrAttachment.file_size', new_callable=PropertyMock)
    def test_mail_mail_send_server_attachment_to_download_link(self, mock_attachment_file_size):
        """ Test that when the mail size exceeds the max email size limit,
        attachments are turned into download links added at the end of the
        email content.

        The feature is tested in the following conditions:
        - using a specified server or the default one (to test command ICP parameter)
        - in batch mode
        - with mail that exceed (with one or more attachments) or not the limit
        - with attachment owned by a business record or not: attachments not owned by a
        business record are never turned into links because their lifespans are not
        controlled by the user (might even be deleted right after the message is sent).
        """
        def count_attachments(message):
            if isinstance(message, str):
                return 0
            elif message.is_multipart():
                return sum(count_attachments(part) for part in message.get_payload())
            elif 'attachment' in message.get('Content-Disposition', ''):
                return 1
            return 0

        mock_attachment_file_size.return_value = 1024 * 128
        # Define some constant to ease the understanding of the test
        test_mail_server = self.mail_server_domain_2
        max_size_always_exceed = 0.1
        max_size_never_exceed = 10

        for n_attachment, mail_server, business_attachment, expected_is_links in (
                # 1 attachment which doesn't exceed max size
                (1, self.env['ir.mail_server'], True, False),
                # 3 attachment: exceed max size
                (3, self.env['ir.mail_server'], True, True),
                # 1 attachment: exceed max size
                (1, self.env['ir.mail_server'], True, True),
                # Same as above with a specific server. Note that the default and server max_email size are reversed.
                (1, test_mail_server, True, False),
                (3, test_mail_server, True, True),
                (1, test_mail_server, True, True),
                # Attachments not linked to a business record are never turned to link
                (3, self.env['ir.mail_server'], False, False),
                (1, test_mail_server, False, False),
        ):
            # Setup max email size to check that the right maximum is used (default or mail server one)
            if expected_is_links:
                max_size_test_succeed = max_size_always_exceed * n_attachment
                max_size_test_fail = max_size_never_exceed
            else:
                max_size_test_succeed = max_size_never_exceed
                max_size_test_fail = max_size_always_exceed * n_attachment
            if mail_server:
                self.env['ir.config_parameter'].sudo().set_param('base.default_max_email_size', max_size_test_fail)
                mail_server.max_email_size = max_size_test_succeed
            else:
                self.env['ir.config_parameter'].sudo().set_param('base.default_max_email_size', max_size_test_succeed)

            attachments = self.env['ir.attachment'].sudo().create([{
                'name': f'attachment{idx_attachment}',
                'res_name': 'test',
                'res_model': self.test_record._name if business_attachment else 'mail.message',
                'res_id': self.test_record.id if business_attachment else 0,
                'datas': 'IA==',  # a non-empty base64 content. We mock attachment file_size to simulate bigger size.
            } for idx_attachment in range(n_attachment)])
            with self.mock_smtplib_connection():
                mails = self.env['mail.mail'].create([{
                    'attachment_ids': attachments.ids,
                    'body_html': '<p>Test</p>',
                    'email_from': 'test@test_2.com',
                    'email_to': f'mail_{mail_idx}@test.com',
                } for mail_idx in range(2)])
                mails._send(mail_server=mail_server)

            self.assertEqual(len(self.emails), 2)
            for mail, outgoing_email in zip(mails, self.emails):
                message_raw = outgoing_email['message']
                message_parsed = message_from_string(message_raw)
                message_cleaned = re.sub(r'[\s=]', '', message_raw)
                with self.subTest(n_attachment=n_attachment, mail_server=mail_server,
                                  business_attachment=business_attachment, expected_is_links=expected_is_links):
                    if expected_is_links:
                        self.assertEqual(count_attachments(message_parsed), 0,
                                         'Attachments should have been removed (replaced by download links)')
                        self.assertTrue(all(attachment.access_token for attachment in attachments),
                                        'Original attachment should have been modified (access_token added)')
                        self.assertTrue(all(attachment.access_token in message_cleaned for attachment in attachments),
                                         'All attachments should have been turned into download links')
                    else:
                        self.assertEqual(count_attachments(message_parsed), n_attachment,
                                         'All attachments should be present')
                        self.assertEqual(message_cleaned.count('access_token'), 0,
                                         'Attachments should not have been turned into download links')
                        self.assertTrue(all(not attachment.access_token for attachment in attachments),
                                        'Original attachment should not have been modified (access_token not added)')


@tagged('mail_mail')
class TestMailMailRace(common.TransactionCase):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_bounce_during_send(self):
        cr = self.registry.cursor()
        env = api.Environment(cr, SUPERUSER_ID, {})

        self.partner = env['res.partner'].create({
            'name': 'Ernest Partner',
        })
        # we need to simulate a mail sent by the cron task, first create mail, message and notification by hand
        mail = env['mail.mail'].sudo().create({
            'body_html': '<p>Test</p>',
            'is_notification': True,
            'state': 'outgoing',
            'recipient_ids': [(4, self.partner.id)]
        })
        mail_message = mail.mail_message_id

        message = env['mail.message'].create({
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
        notif = env['mail.notification'].search([('res_partner_id', '=', self.partner.id)])
        # we need to commit transaction or cr will keep the lock on notif
        cr.commit()

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

        self.patch(self.registry['ir.mail_server'], 'send_email', send_email)

        mail.send()

        self.assertTrue(bounce_deferred, "The bounce should have been deferred")
        self.assertEqual(notif.notification_status, 'sent')

        # some cleaning since we commited the cr

        notif.unlink()
        mail.unlink()
        (mail_message | message).unlink()
        self.partner.unlink()
        cr.commit()
        cr.close()
