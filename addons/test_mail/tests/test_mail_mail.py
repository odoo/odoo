# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2
import pytz

from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import call

from odoo import api, tools
from odoo.addons.base.tests.common import MockSmtplibCase
from odoo.addons.test_mail.tests.common import TestMailCommon
from odoo.tests import common, tagged
from odoo.tools import mute_logger, DEFAULT_SERVER_DATETIME_FORMAT


@tagged('mail_mail')
class TestMailMail(TestMailCommon, MockSmtplibCase):

    @classmethod
    def setUpClass(cls):
        super(TestMailMail, cls).setUpClass()
        cls._init_mail_gateway()
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

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_message_notify_from_mail_mail(self):
        # Due ot post-commit hooks, store send emails in every step
        mail = self.env['mail.mail'].sudo().create({
            'body_html': '<p>Test</p>',
            'email_to': 'test@example.com',
            'partner_ids': [(4, self.user_employee.partner_id.id)]
        })
        with self.mock_mail_gateway():
            mail.send()
        self.assertSentEmail(mail.env.user.partner_id, ['test@example.com'])
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
