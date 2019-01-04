# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import time

from collections import defaultdict
from contextlib import contextmanager
from email.utils import formataddr
from functools import partial
from unittest.mock import patch
from smtplib import SMTPServerDisconnected

from odoo.addons.base.models.ir_mail_server import IrMailServer, MailDeliveryException
from odoo.addons.bus.models.bus import ImBus, json_dump
from odoo.addons.mail.models.mail_mail import MailMail
from odoo.addons.mail.models.mail_message import Message
from odoo.addons.mail.models.mail_notification import Notification
from odoo.tests import common, new_test_user

mail_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class MockEmail(common.BaseCase):

    @contextmanager
    def mock_mail_gateway(self, sim_error=None):
        build_email_origin = IrMailServer.build_email
        mail_create_origin = MailMail.create
        self._init_mail_mock()

        def _ir_mail_server_connect(model, *args, **kwargs):
            return None

        def _ir_mail_server_build_email(model, *args, **kwargs):
            self._mails.append(kwargs)
            self._mails_args.append(args)
            return build_email_origin(model, *args, **kwargs)

        def _ir_mail_server_send_email(model, message, *args, **kwargs):
            if sim_error and sim_error == 'send_assert':
                raise AssertionError('Bliobli')
            elif sim_error and sim_error == 'send_disconnect':
                raise SMTPServerDisconnected('Blablou')
            elif sim_error and sim_error == 'send_delivery':
                raise MailDeliveryException('Some message')
            return message['Message-Id']

        def _mail_mail_create(model, *args, **kwargs):
            res = mail_create_origin(model, *args, **kwargs)
            self._new_mails += res.sudo()
            return res

        try:
            with patch.object(IrMailServer, 'connect', autospec=True, wraps=IrMailServer, side_effect=_ir_mail_server_connect) as ir_mail_server_connect_mock, \
                    patch.object(IrMailServer, 'build_email', autospec=True, wraps=IrMailServer, side_effect=_ir_mail_server_build_email) as ir_mail_server_build_email_mock, \
                    patch.object(IrMailServer, 'send_email', autospec=True, wraps=IrMailServer, side_effect=_ir_mail_server_send_email) as ir_mail_server_send_email_mock, \
                    patch.object(MailMail, 'create', autospec=True, wraps=MailMail, side_effect=_mail_mail_create) as _mail_mail_create_mock, \
                    patch.object(MailMail, 'unlink', return_value=True) as mail_mail_unlink_mock:
                yield
        finally:
            pass

    @classmethod
    def _init_mail_mock(self):
        self._mails = []
        self._mails_args = []
        self._new_mails = self.env['mail.mail'].sudo()

    # ------------------------------------------------------------
    # GATEWAY TOOLS
    # ------------------------------------------------------------

    def format(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
               extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
               cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>'):
        return template.format(to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)

    def format_and_process(self, template, email_from, to, subject='Frogs', extra='',  cc='', msg_id=False,
                           model=None, target_model='mail.test.gateway', target_field='name'):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        if not msg_id:
            msg_id = "<%.7f-test@iron.sky>" % (time.time())

        mail = self.format(template, to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)
        self.env['mail.thread'].with_context(mail_channel_noautofollow=True).message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])

    @classmethod
    def _init_mail_gateway(cls):
        cls.alias_domain = 'test.com'
        cls.alias_catchall = 'catchall.test'
        cls.alias_bounce = 'bounce.test'
        cls.env['ir.config_parameter'].set_param('mail.bounce.alias', cls.alias_bounce)
        cls.env['ir.config_parameter'].set_param('mail.catchall.domain', cls.alias_domain)
        cls.env['ir.config_parameter'].set_param('mail.catchall.alias', cls.alias_catchall)

    # ------------------------------------------------------------
    # GATEWAY ASSERTS
    # ------------------------------------------------------------

    def assertSentMail(self, author, recipients, message, **values):
        mail = next((mail for mail in self._new_mails if mail.mail_message_id == message), False)
        self.assertTrue(bool(mail), 'mail.mail not found from %s' % (author))
        for recipient in recipients:
            self.assertSentEmail(author, [recipient], **values)

    def assertOutgoingMail(self):
        # do something for unlinked mails
        self.assertSentEmail()

    def assertNotSentEmail(self, author):
        self.assertEqual(len(self._mails), 0)

    def assertSentEmail(self, author, recipients, **values):
        """ Tool method to ease the check of send emails.

        :param recipients_info: list of [(author, recipients)]
        :param values: dictionary of values to check in all emails (same for all)
        """
        base_expected = {}
        for fname in ['reply_to', 'subject', 'attachments', 'body', 'references',
                      'body_content', 'body_alternative_content', 'references_content']:
            if fname in values:
                base_expected[fname] = values[fname]

        expected = dict(base_expected)
        if isinstance(author, self.env['res.partner'].__class__):
            expected['email_from'] = formataddr((author.name, author.email))
        else:
            expected['email_from'] = author

        email_to_list = []
        for email_to in recipients:
            if isinstance(email_to, self.env['res.partner'].__class__):
                email_to_list.append(formataddr((email_to.name, email_to.email)))
            else:
                email_to_list.append(email_to)
        expected['email_to'] = email_to_list

        sent_mail = next(
            (mail for mail in self._mails
             if set(mail['email_to']) == set(expected['email_to']) and mail['email_from'] == expected['email_from']
             ), False)
        self.assertTrue(bool(sent_mail), 'Expected mail from %s to %s not found' % (expected['email_from'], expected['email_to']))
        for val in ['reply_to', 'subject', 'body', 'references', 'attachments']:
            if val in expected:
                self.assertEqual(expected[val], sent_mail[val], 'Value for %s: expected %s, received %s' % (val, expected[val], sent_mail[val]))
        for val in ['body_content', 'body_alternative', 'references_content']:
            if val in expected:
                self.assertIn(expected[val], sent_mail[val[:-8]], 'Value for %s: %s does not contain %s' % (val, sent_mail[val[:-8]], expected[val]))


class MailCase(MockEmail):
    """ Tools, helpers and asserts for mail-related tests, including mail
    gateway mock and helpers (see ´´MockEmail´´).

    Useful reminders
        Notif type:  ('inbox', 'Inbox'), ('email', 'Email')
        Notif status: ('ready', 'Ready to Send'), ('sent', 'Sent'),
                      ('bounce', 'Bounced'), ('exception', 'Exception'),
                      ('canceled', 'Canceled')
        Notif failure type: ("SMTP", "Connection failed (outgoing mail server problem)"),
                            ("RECIPIENT", "Invalid email address"),
                            ("BOUNCE", "Email address rejected by destination"),
                            ("UNKNOWN", "Unknown error")
    """
    _test_context = {
        'mail_create_nolog': True,
        'mail_create_nosubscribe': True,
        'mail_notrack': True,
        'no_reset_password': True
    }

    @classmethod
    def _reset_mail_context(cls, record):
        return record.with_context(
            mail_create_nolog=False,
            mail_create_nosubscribe=False,
            mail_notrack=False
        )

    # ------------------------------------------------------------
    # MAIL MOCKS
    # ------------------------------------------------------------

    @contextmanager
    def mock_mail_app(self):
        message_create_origin = Message.create
        notification_create_origin = Notification.create
        self._init_mock_mail()

        def _mail_message_create(model, *args, **kwargs):
            res = message_create_origin(model, *args, **kwargs)
            self._new_msgs += res.sudo()
            return res

        def _mail_notification_create(model, *args, **kwargs):
            res = notification_create_origin(model, *args, **kwargs)
            self._new_notifs += res.sudo()
            return res

        try:
            with patch.object(Message, 'create', autospec=True, wraps=Message, side_effect=_mail_message_create) as _mail_message_create_mock, \
                    patch.object(Notification, 'create', autospec=True, wraps=Notification, side_effect=_mail_notification_create) as _mail_notification_create_mock:
                yield
        finally:
            pass

    def _init_mock_mail(self):
        self._new_msgs = self.env['mail.message'].sudo()
        self._new_notifs = self.env['mail.notification'].sudo()

    # ------------------------------------------------------------
    # MAIL MODELS ASSERTS
    # ------------------------------------------------------------

    @contextmanager
    def assertNotifications(self, recipients_info, sim_error=None):
        """ Check content of notifications.

          :param recipients_info: list of data dict: [{
            'partner': res.partner record (may be empty),
            'status': notification_status to check,
            'type': notification_type to check,
            'is_read': is_read to check,
            'failure_type': optional: one of failure_type key
            'count': optional: if there are more than 1 similar notification (FIXME)
            }, { ... }]
        """
        try:
            with self.mock_mail_gateway(sim_error=sim_error), self.mock_mail_app():
                yield
        finally:
            done_msgs = self.env['mail.message'].sudo()
            done_notifs = self.env['mail.notification'].sudo()

            for message_info in recipients_info:
                mbody, mtype = message_info['content'], message_info.get('message_type', 'comment')
                msubtype = self.env.ref(message_info.get('subtype', 'mail.mt_comment'))
                message = self._new_msgs.filtered(lambda message: mbody in message.body and message.message_type == mtype and message.subtype_id == msubtype)
                self.assertTrue(message, 'Mail: not found message (content: %s, message_type: %s)' % (mbody, mtype))

                # assert notifications
                group_to_recipients = defaultdict(list)
                for recipient in message_info['notif']:
                    partner, ntype, ngroup, nstatus = recipient['partner'], recipient['type'], recipient.get('group'), recipient.get('status', 'sent')
                    nis_read = recipient.get('is_read', False if recipient['type'] == 'inbox' else True)
                    if not ngroup:
                        ngroup = 'user'
                        if partner and not partner.user_ids:
                            ngroup = 'customer'
                        elif partner and partner.partner_share:
                            ngroup = 'portal'

                    partner_notif = self._new_notifs.filtered(
                        lambda n: n.mail_message_id == message and
                        n.res_partner_id == partner and
                        n.notification_type == ntype and
                        n.notification_status == nstatus and
                        n.is_read == nis_read
                    )
                    self.assertTrue(partner_notif, 'Mail: not found notification for %s (type: %s, state: %s, message: %s)' % (partner, ntype, nstatus, message.id))
                    if ntype == 'email':
                        group_to_recipients[ngroup].append(partner)
                    done_notifs |= partner_notif
                done_msgs |= message

                # compute emails that should be sent (hint: mail.mail per group, email par recipient)
                for recipients in group_to_recipients.values():
                    self.assertSentMail(message.author_id if message.author_id else message.email_from, recipients, message, body_content=mbody)

            self.assertEqual(self._new_msgs, done_msgs, 'Mail: invalid message creation (%s) / expected (%s)' % (len(self._new_msgs), len(done_msgs)))
            self.assertEqual(self._new_notifs, done_notifs, 'Mail: invalid notification creation (%s) / expected (%s)' % (len(self._new_notifs), len(done_notifs)))

    def assertBusNotification(self, channels, message_items=None, init=True):
        """ Check for bus notifications. Basic check is about used channels.
        Verifying content is optional.

        (self.cr.dbname, 'mail.channel', self.channel_1.id)
        (self.cr.dbname, 'res.partner', self.partner_employee_2.id)

        :param channels: list of channel
        :param message_items: if given, list of message making a valid pair (channel,
          message) to be found in bus.bus
        """
        def check_content(returned_value, expected_value):
            if isinstance(expected_value, list):
                done = []
                for expected_item in expected_value:
                    for returned_item in returned_value:
                        if check_content(returned_item, expected_item):
                            done.append(expected_item)
                            break
                    else:
                        return False
                return len(done) == len(expected_value)
            elif isinstance(expected_value, dict):
                return all(k in returned_value for k in expected_value.keys()) and all(
                    check_content(returned_value[key], val)
                    for key, val in expected_value.items()
                )
            else:
                return returned_value == expected_value

        if init:
            self.assertEqual(len(self.env['bus.bus'].search([])), len(channels))
        notifications = self.env['bus.bus'].search([('channel', 'in', [json_dump(channel) for channel in channels])])
        notif_messages = [json.loads(n.message) for n in notifications]
        self.assertEqual(len(notifications), len(channels))

        for expected in message_items or []:
            for notification in notif_messages:
                found_keys, not_found_keys = [], []
                if not all(k in notification for k in expected.keys()):
                    continue
                for expected_key, expected_value in expected.items():
                    done = check_content(notification[expected_key], expected_value)
                    if done:
                        found_keys.append(expected_key)
                    else:
                        not_found_keys.append(expected_key)
                if set(found_keys) == set(expected.keys()):
                    break
            else:
                raise AssertionError('Keys %s not found (expected: %s - returned: %s)' % (not_found_keys, repr(expected), repr(notif_messages)))

    def assertTracking(self, message, data):
        tracking_values = message.sudo().tracking_value_ids
        for field_name, value_type, old_value, new_value in data:
            tracking = tracking_values.filtered(lambda track: track.field == field_name)
            self.assertEqual(len(tracking), 1)
            if value_type in ('char', 'integer'):
                self.assertEqual(tracking.old_value_char, old_value)
                self.assertEqual(tracking.new_value_char, new_value)
            elif value_type in ('many2one'):
                self.assertEqual(tracking.old_value_integer, old_value and old_value.id or False)
                self.assertEqual(tracking.new_value_integer, new_value and new_value.id or False)
                self.assertEqual(tracking.old_value_char, old_value and old_value.display_name or '')
                self.assertEqual(tracking.new_value_char, new_value and new_value.display_name or '')
            else:
                self.assertEqual(1, 0)
