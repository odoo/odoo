# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import email
import email.policy
import time

from collections import defaultdict
from contextlib import contextmanager
from functools import partial
from unittest.mock import patch
from smtplib import SMTPServerDisconnected

from odoo import exceptions
from odoo.addons.base.models.ir_mail_server import IrMailServer, MailDeliveryException
from odoo.addons.bus.models.bus import ImBus, json_dump
from odoo.addons.mail.models.mail_mail import MailMail
from odoo.addons.mail.models.mail_message import Message
from odoo.addons.mail.models.mail_notification import MailNotification
from odoo.tests import common, new_test_user
from odoo.tools import formataddr, pycompat

mail_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class MockEmail(common.BaseCase):
    """ Tools, helpers and asserts for mailgateway-related tests

    Useful reminders
        Mail state: ('outgoing', 'Outgoing'), ('sent', 'Sent'),
                    ('received', 'Received'), ('exception', 'Delivery Failed'),
                    ('cancel', 'Cancelled')
    """

    @contextmanager
    def mock_mail_gateway(self, mail_unlink_sent=False, sim_error=None):
        build_email_origin = IrMailServer.build_email
        mail_create_origin = MailMail.create
        mail_unlink_origin = MailMail.unlink
        self._init_mail_mock()
        self.mail_unlink_sent = mail_unlink_sent

        def _ir_mail_server_connect(model, *args, **kwargs):
            if sim_error and sim_error == 'connect_smtp_notfound':
                raise exceptions.UserError(
                    "Missing SMTP Server\nPlease define at least one SMTP server, or provide the SMTP parameters explicitly.")
            if sim_error and sim_error == 'connect_failure':
                raise Exception("Some exception")
            return None

        def _ir_mail_server_build_email(model, *args, **kwargs):
            self._mails.append(kwargs)
            self._mails_args.append(args)
            return build_email_origin(model, *args, **kwargs)

        def _ir_mail_server_send_email(model, message, *args, **kwargs):
            if '@' not in message['To']:
                raise AssertionError(model.NO_VALID_RECIPIENT)
            if sim_error and sim_error == 'send_assert':
                raise AssertionError('AssertionError')
            elif sim_error and sim_error == 'send_disconnect':
                raise SMTPServerDisconnected('SMTPServerDisconnected')
            elif sim_error and sim_error == 'send_delivery':
                raise MailDeliveryException('MailDeliveryException')
            return message['Message-Id']

        def _mail_mail_create(model, *args, **kwargs):
            res = mail_create_origin(model, *args, **kwargs)
            self._new_mails += res.sudo()
            return res

        def _mail_mail_unlink(model, *args, **kwargs):
            if self.mail_unlink_sent:
                return mail_unlink_origin(model, *args, **kwargs)
            return True

        with patch.object(IrMailServer, 'connect', autospec=True, wraps=IrMailServer, side_effect=_ir_mail_server_connect) as ir_mail_server_connect_mock, \
                patch.object(IrMailServer, 'build_email', autospec=True, wraps=IrMailServer, side_effect=_ir_mail_server_build_email) as ir_mail_server_build_email_mock, \
                patch.object(IrMailServer, 'send_email', autospec=True, wraps=IrMailServer, side_effect=_ir_mail_server_send_email) as ir_mail_server_send_email_mock, \
                patch.object(MailMail, 'create', autospec=True, wraps=MailMail, side_effect=_mail_mail_create) as _mail_mail_create_mock, \
                patch.object(MailMail, 'unlink', autospec=True, wraps=MailMail, side_effect=_mail_mail_unlink) as mail_mail_unlink_mock:
            yield

    def _init_mail_mock(self):
        self._mails = []
        self._mails_args = []
        self._new_mails = self.env['mail.mail'].sudo()

    # ------------------------------------------------------------
    # GATEWAY TOOLS
    # ------------------------------------------------------------

    @classmethod
    def _init_mail_gateway(cls):
        cls.alias_domain = 'test.com'
        cls.alias_catchall = 'catchall.test'
        cls.alias_bounce = 'bounce.test'
        cls.env['ir.config_parameter'].set_param('mail.bounce.alias', cls.alias_bounce)
        cls.env['ir.config_parameter'].set_param('mail.catchall.domain', cls.alias_domain)
        cls.env['ir.config_parameter'].set_param('mail.catchall.alias', cls.alias_catchall)
        cls.mailer_daemon_email = formataddr(('MAILER-DAEMON', '%s@%s' % (cls.alias_bounce, cls.alias_domain)))

    def format(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
               email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>', return_path='', cc='',
               extra='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>'):
        return template.format(
            subject=subject, to=to, cc=cc,
            email_from=email_from, return_path=return_path,
            extra=extra, msg_id=msg_id)

    def format_and_process(self, template, email_from, to, subject='Frogs', cc='',
                           return_path='', extra='',  msg_id=False,
                           model=None, target_model='mail.test.gateway', target_field='name'):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        if not msg_id:
            msg_id = "<%.7f-test@iron.sky>" % (time.time())

        mail = self.format(template, to=to, subject=subject, cc=cc, return_path=return_path, extra=extra, email_from=email_from, msg_id=msg_id)
        self.env['mail.thread'].with_context(mail_channel_noautofollow=True).message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])

    def gateway_reply_wrecord(self, template, record, use_in_reply_to=True):
        """ Simulate a reply through the mail gateway. Usage: giving a record,
        find an email sent to him and use its message-ID to simulate a reply.

        Some noise is added in References just to test some robustness. """
        mail_mail = self._find_mail_mail_wrecord(record)

        if use_in_reply_to:
            extra = 'In-Reply-To:\r\n\t%s\n' % mail_mail.message_id
        else:
            disturbing_other_msg_id = '<123456.654321@another.host.com>'
            extra = 'References:\r\n\t%s\n\r%s' % (mail_mail.message_id, disturbing_other_msg_id)

        return self.format_and_process(
            template,
            mail_mail.email_to,
            mail_mail.reply_to,
            subject='Re: %s' % mail_mail.subject,
            extra=extra,
            msg_id='<123456.%s.%d@test.example.com>' % (record._name, record.id),
            target_model=record._name,
            target_field=record._rec_name,
        )

    def from_string(self, text):
        return email.message_from_string(pycompat.to_text(text), policy=email.policy.SMTP)

    def assertHtmlEqual(self, value, expected, message=None):
        from lxml import html

        tree = html.fragment_fromstring(value, parser=html.HTMLParser(encoding='utf-8'), create_parent='body')

        # mass mailing: add base tag we have to remove
        for base_node in tree.xpath('//base'):
            base_node.getparent().remove(base_node)

        # chatter: read more / read less TODO

        # mass mailing: add base tag we have to remove
        expected_node = html.fragment_fromstring(expected, create_parent='body')

        if message:
            self.assertEqual(tree, expected_node, message)
        else:
            self.assertEqual(tree, expected_node)

    # ------------------------------------------------------------
    # GATEWAY ASSERTS
    # ------------------------------------------------------------

    def _find_sent_mail_wemail(self, email_to):
        for email in self._mails:
            if set(email['email_to']) == set([email_to]):
                break
        else:
            raise AssertionError('sent mail not found for email_to %s' % (email_to))
        return email


    def _find_mail_mail_wpartners(self, recipients, status, mail_message=None, author=None):
        for mail in self._new_mails:
            if author is not None and mail.author_id != author:
                continue
            if mail_message is not None and mail.mail_message_id != mail_message:
                continue
            if status and mail.state != status:
                continue
            if all(p in mail.recipient_ids for p in recipients):
                break
        else:
            raise AssertionError('mail.mail not found for message %s / status %s / recipients %s' % (mail_message, status, recipients.ids))
        return mail

    def _find_mail_mail_wemail(self, email_to, status, mail_message=None, author=None):
        for mail in self._new_mails:
            if author is not None and mail.author_id != author:
                continue
            if mail_message is not None and mail.mail_message_id != mail_message:
                continue
            if status and mail.state != status:
                continue
            if (mail.email_to == email_to and not mail.recipient_ids) or (not mail.email_to and mail.recipient_ids.email) == email_to:
                break
        else:
            raise AssertionError('mail.mail not found for email_to %s / status %s in %s' % (email_to, status, repr([m.email_to for m in self._new_mails])))
        return mail

    def _find_mail_mail_wrecord(self, record):
        for mail in self._new_mails:
            if mail.model == record._name and mail.res_id == record.id:
                break
        else:
            raise AssertionError('mail.mail not found for record %s in %s' % (record, repr([m.email_to for m in self._new_mails])))
        return mail

    def assertMailFailed(self, author, recipients, mail_message):
        mail = self._find_mail(author, recipients, mail_message)
        self.assertEqual(mail.state, 'exception')

    def assertMailMail(self, recipients, status, check_mail_mail=True, mail_message=None, author=None, email_values=None):
        if check_mail_mail:
            mail = self._find_mail_mail_wpartners(recipients, status, mail_message=mail_message, author=author)
            self.assertTrue(bool(mail))
        if status == 'sent':
            for recipient in recipients:
                self.assertSentEmail(author, [recipient], **email_values)

    def assertMailMailWEmails(self, emails, status, content, fields_values=None):
        """ Will check in self._new_mails to find a sent mail.mail. To use with
        mail gateway mock.

        :param emails: list of emails;
        :param status: status of mail.mail;
        :param content: content to check for each email;
        :param fields_values: specific value to check on the mail.mail record;
        """
        for email_to in emails:
            sent_mail = self._find_mail_mail_wemail(email_to, status)
            if content:
                self.assertIn(content, sent_mail.body_html)
            for fname, fvalue in (fields_values or {}).items():
                self.assertEqual(sent_mail[fname], fvalue)

    def assertNoMail(self, author, recipients, mail_message):
        try:
            self._find_mail_mail_wpartners(recipients, False, mail_message=mail_message, author=author)
        except AssertionError:
            pass
        else:
            raise AssertionError('mail.mail exists for message %s / recipients %s but should not exist' % (mail_message, recipients.ids))
        finally:
            self.assertNotSentEmail()

    def assertNotSentEmail(self):
        self.assertEqual(len(self._mails), 0)

    def assertSentEmail(self, author, recipients, **values):
        """ Tool method to ease the check of send emails.

        :param author: email author, either a string (email), either a partner
          record;
        :param recipients: list of recipients, each being either a string (email),
          either a partner record;
        :param values: dictionary of additional values to check email content;
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
        debug_info = '-'.join('From: %s-To: %s' % (mail['email_from'], mail['email_to']) for mail in self._mails) if not bool(sent_mail) else ''
        self.assertTrue(bool(sent_mail), 'Expected mail from %s to %s not found in %s' % (expected['email_from'], expected['email_to'], debug_info))

        for val in ['reply_to', 'subject', 'references', 'attachments']:
            if val in expected:
                self.assertEqual(expected[val], sent_mail[val], 'Value for %s: expected %s, received %s' % (val, expected[val], sent_mail[val]))
        for val in ['body']:
            if val in expected:
                self.assertHtmlEqual(expected[val], sent_mail[val], 'Value for %s: expected %s, received %s' % (val, expected[val], sent_mail[val]))
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

    def flush_tracking(self):
        """ Force the creation of tracking values. """
        self.env['base'].flush()
        self.cr.precommit.run()

    # ------------------------------------------------------------
    # MAIL MOCKS
    # ------------------------------------------------------------

    @contextmanager
    def mock_bus(self):
        bus_bus_create_origin = ImBus.create
        self._init_mock_bus()

        def _bus_bus_create(model, *args, **kwargs):
            res = bus_bus_create_origin(model, *args, **kwargs)
            self._new_bus_notifs += res.sudo()
            return res

        with patch.object(ImBus, 'create', autospec=True, wraps=ImBus, side_effect=_bus_bus_create) as _bus_bus_create_mock:
            yield

    def _init_mock_bus(self):
        self._new_bus_notifs = self.env['bus.bus'].sudo()

    def _reset_bus(self):
        self.env['bus.bus'].sudo().search([]).unlink()

    @contextmanager
    def mock_mail_app(self):
        message_create_origin = Message.create
        notification_create_origin = MailNotification.create
        self._init_mock_mail()

        def _mail_message_create(model, *args, **kwargs):
            res = message_create_origin(model, *args, **kwargs)
            self._new_msgs += res.sudo()
            return res

        def _mail_notification_create(model, *args, **kwargs):
            res = notification_create_origin(model, *args, **kwargs)
            self._new_notifs += res.sudo()
            return res

        with patch.object(Message, 'create', autospec=True, wraps=Message, side_effect=_mail_message_create) as _mail_message_create_mock, \
                patch.object(MailNotification, 'create', autospec=True, wraps=MailNotification, side_effect=_mail_notification_create) as _mail_notification_create_mock:
            yield

    def _init_mock_mail(self):
        self._new_msgs = self.env['mail.message'].sudo()
        self._new_notifs = self.env['mail.notification'].sudo()

    # ------------------------------------------------------------
    # MAIL TOOLS
    # ------------------------------------------------------------

    @classmethod
    def _add_messages(cls, record, body_content, count=1, author=None, **kwargs):
        """ Helper: add #count messages in record history """
        author = author if author else cls.env.user.partner_id
        if 'email_from' not in kwargs:
            kwargs['email_from'] = author.email_formatted
        subtype_id = kwargs.get('subtype_id', cls.env.ref('mail.mt_comment').id)

        values = {
            'model': record._name,
            'res_id': record.id,
            'author_id': author.id,
            'subtype_id': subtype_id,
        }
        values.update(kwargs)

        create_vals = [dict(
            values, body='%s/%02d' % (body_content, counter))
            for counter in range(count)]

        return cls.env['mail.message'].sudo().create(create_vals)

    @classmethod
    def _create_template(cls, model, template_values=None):
        create_values = {
            'name': 'TestTemplate',
            'subject': 'About ${object.name}',
            'body_html': '<p>Hello ${object.name}</p>',
            'model_id': cls.env['ir.model']._get(model).id,
        }
        if template_values:
            create_values.update(template_values)
        cls.email_template = cls.env['mail.template'].create(create_values)
        return cls.email_template


    def _generate_notify_recipients(self, partners):
        """ Tool method to generate recipients data according to structure used
        in notification methods. Purpose is to allow testing of internals of
        some notification methods, notably testing links or group-based notification
        details.

        See notably ``MailThread._notify_compute_recipients()``.
        """
        return [
            {'id': partner.id,
             'active': True,
             'share': partner.partner_share,
             'groups': partner.user_ids.groups_id.ids,
             'notif': partner.user_ids.notification_type or 'email',
             'type': 'user' if partner.user_ids and not partner.partner_share else partner.user_ids and 'portal' or 'customer',
            } for partner in partners
        ]

    # ------------------------------------------------------------
    # MAIL ASSERTS WRAPPERS
    # ------------------------------------------------------------

    @contextmanager
    def assertSinglePostNotifications(self, recipients_info, message_info=None, mail_unlink_sent=False, sim_error=None):
        """ Shortcut to assertMsgNotifications when having a single message to check. """
        r_info = dict(message_info if message_info else {})
        r_info.setdefault('content', '')
        r_info['notif'] = recipients_info
        with self.assertPostNotifications([r_info], mail_unlink_sent=mail_unlink_sent, sim_error=sim_error):
            yield

    @contextmanager
    def assertPostNotifications(self, recipients_info, mail_unlink_sent=False, sim_error=None):
        """ Check content of notifications. """
        try:
            with self.mock_mail_gateway(mail_unlink_sent=mail_unlink_sent, sim_error=sim_error), self.mock_bus(), self.mock_mail_app():
                yield
        finally:
            done_msgs, done_notifs = self.assertMailNotifications(self._new_msgs, recipients_info)
            self.assertEqual(self._new_msgs, done_msgs, 'Mail: invalid message creation (%s) / expected (%s)' % (len(self._new_msgs), len(done_msgs)))
            self.assertEqual(self._new_notifs, done_notifs, 'Mail: invalid notification creation (%s) / expected (%s)' % (len(self._new_notifs), len(done_notifs)))

    @contextmanager
    def assertBus(self, channels, message_items=None):
        """ Check content of bus notifications. """
        try:
            with self.mock_bus():
                yield
        finally:
            found_bus_notifs = self.assertBusNotifications(channels, message_items=message_items)
            self.assertEqual(self._new_bus_notifs, found_bus_notifs)

    @contextmanager
    def assertNoNotifications(self):
        try:
            with self.mock_mail_gateway(mail_unlink_sent=False, sim_error=None), self.mock_bus(), self.mock_mail_app():
                yield
        finally:
            self.assertFalse(bool(self._new_msgs))
            self.assertFalse(bool(self._new_notifs))

    # ------------------------------------------------------------
    # MAIL MODELS ASSERTS
    # ------------------------------------------------------------

    def assertMailNotifications(self, messages, recipients_info):
        """ Check bus notifications content. Mandatory and basic check is about
        channels being notified. Content check is optional.

        GNERATED INPUT
        :param messages: generated messages to check;

        EXPECTED
        :param recipients_info: list of data dict: [
          {'content': message content,
           'message_type': message_type (default: 'comment'),
           'subtype': xml id of message subtype (default: 'mail.mt_comment'),
           'notif': list of notified recipients: [
             {'partner': res.partner record (may be empty),
              'email': NOT SUPPORTED YET,
              'status': notification_status to check,
              'type': notification_type to check,
              'is_read': is_read to check,
              'check_send': whether outgoing stuff has to be checked;
              'failure_type': optional: one of failure_type key
             }, { ... }]
          }, {...}]

        PARAMETERS
        :param unlink_sent: to know whether to compute
        """
        partners = self.env['res.partner'].sudo().concat(*list(p['partner'] for i in recipients_info for p in i['notif'] if p.get('partner')))
        base_domain = [('res_partner_id', 'in', partners.ids)]
        if messages is not None:
            base_domain += [('mail_message_id', 'in', messages.ids)]
        notifications = self.env['mail.notification'].sudo().search(base_domain)

        done_msgs = self.env['mail.message'].sudo()
        done_notifs = self.env['mail.notification'].sudo()

        for message_info in recipients_info:
            mbody, mtype = message_info.get('content', ''), message_info.get('message_type', 'comment')
            msubtype = self.env.ref(message_info.get('subtype', 'mail.mt_comment'))

            # find message
            if messages:
                message = messages.filtered(lambda message: mbody in message.body and message.message_type == mtype and message.subtype_id == msubtype)
            else:
                message = self.env['mail.message'].sudo().search([('body', 'ilike', mbody), ('message_type', '=', mtype), ('subtype_id', '=', msubtype.id)], limit=1, order='id DESC')
            self.assertTrue(message, 'Mail: not found message (content: %s, message_type: %s, subtype: %s)' % (mbody, mtype, msubtype.name))

            # check notifications and prepare assert data
            email_groups = defaultdict(list)
            mail_groups = {'failure': []}
            for recipient in message_info['notif']:
                partner, ntype, ngroup, nstatus = recipient['partner'], recipient['type'], recipient.get('group'), recipient.get('status', 'sent')
                nis_read, ncheck_send = recipient.get('is_read', False if recipient['type'] == 'inbox' else True), recipient.get('check_send', True)
                if not ngroup:
                    ngroup = 'user'
                    if partner and not partner.user_ids:
                        ngroup = 'customer'
                    elif partner and partner.partner_share:
                        ngroup = 'portal'

                # find notification
                partner_notif = notifications.filtered(
                    lambda n: n.mail_message_id == message and
                    n.res_partner_id == partner and
                    n.notification_type == ntype and
                    n.notification_status == nstatus and
                    n.is_read == nis_read
                )
                self.assertTrue(partner_notif, 'Mail: not found notification for %s (type: %s, state: %s, message: %s)' % (partner, ntype, nstatus, message.id))

                # prepare further asserts
                if ntype == 'email':
                    if nstatus == 'sent':
                        if ncheck_send:
                            email_groups[ngroup].append(partner)
                    elif nstatus == 'exception':
                        mail_groups['failure'].append(partner)
                        if ncheck_send:
                            email_groups[ngroup].append(partner)
                    elif nstatus == 'canceled':
                        pass
                    else:
                        raise NotImplementedError()

                done_notifs |= partner_notif
            done_msgs |= message

            # check bus notifications that should be sent (hint: message author, multiple notifications)
            bus_notifications = message.notification_ids._filtered_for_web_client().filtered(lambda n: n.notification_status == 'exception')
            if bus_notifications:
                self.assertMessageBusNotifications(message)

            # check emails that should be sent (hint: mail.mail per group, email par recipient)
            for recipients in email_groups.values():
                partners = self.env['res.partner'].sudo().concat(*recipients)
                if all(p in mail_groups['failure'] for p in partners):
                    self.assertMailMail(partners, 'exception', author=message.author_id, mail_message=message)
                else:
                    check_mail_mail = not self.mail_unlink_sent
                    self.assertMailMail(
                        partners, 'sent',
                        author=message.author_id if message.author_id else message.email_from,
                        mail_message=message,
                        check_mail_mail=check_mail_mail,
                        email_values={'body_content': mbody}
                    )
            if not any(p for recipients in email_groups.values() for p in recipients):
                self.assertNoMail(message.author_id, partners, message)

        return done_msgs, done_notifs

    def assertMessageBusNotifications(self, message):
        """Asserts that the expected notification updates have been sent on the
        bus for the given message."""
        self.assertBusNotifications(
            [(self.cr.dbname, 'res.partner', message.author_id.id)],
            [{
                'type': 'message_notification_update',
                'elements': message._message_notification_format(),
            }],
            check_unique=False
        )

    def assertBusNotifications(self, channels, message_items=None, check_unique=True):
        """ Check bus notifications content. Mandatory and basic check is about
        channels being notified. Content check is optional.

        EXPECTED
        :param channels: list of expected bus channels, like [
          (self.cr.dbname, 'mail.channel', self.channel_1.id),
          (self.cr.dbname, 'res.partner', self.partner_employee_2.id)
        ]
        :param message_items: if given, list of expected message making a valid
          pair (channel, message) to be found in bus.bus, like [
            {'type': 'message_notification_update',
             'elements': {self.msg.id: {
                'message_id': self.msg.id,
                'message_type': 'sms',
                'notifications': {...},
                ...
              }}
            }, {...}]
        """
        bus_notifs = self.env['bus.bus'].sudo().search([('channel', 'in', [json_dump(channel) for channel in channels])])
        if check_unique:
            self.assertEqual(len(bus_notifs), len(channels))
        self.assertEqual(set(bus_notifs.mapped('channel')), set([json_dump(channel) for channel in channels]))

        notif_messages = [n.message for n in bus_notifs]

        for expected in message_items or []:
            for notification in notif_messages:
                if json_dump(expected) == notification:
                    break
            else:
                raise AssertionError('No notification was found with the expected value.\nExpected:\n%s\nReturned:\n%s' %
                    (json_dump(expected), '\n'.join([n for n in notif_messages])))

        return bus_notifs

    def assertTracking(self, message, data):
        tracking_values = message.sudo().tracking_value_ids
        for field_name, value_type, old_value, new_value in data:
            tracking = tracking_values.filtered(lambda track: track.field.name == field_name)
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


class MailCommon(common.SavepointCase, MailCase):
    """ Almost-void class definition setting the savepoint case + mock of mail.
    Used mainly for class inheritance in other applications and test modules. """

    @classmethod
    def setUpClass(cls):
        super(MailCommon, cls).setUpClass()
        # give default values for all email aliases and domain
        cls._init_mail_gateway()
        # ensure admin configuration
        cls.user_admin = cls.env.ref('base.user_admin')
        cls.user_admin.write({'notification_type': 'inbox'})
        cls.partner_admin = cls.env.ref('base.partner_admin')
        cls.company_admin = cls.user_admin.company_id
        cls.company_admin.write({'email': 'company@example.com'})

        # test standard employee
        cls.user_employee = mail_new_test_user(
            cls.env, login='employee',
            groups='base.group_user',
            company_id=cls.company_admin.id,
            name='Ernest Employee',
            notification_type='inbox',
            signature='--\nErnest'
        )
        cls.partner_employee = cls.user_employee.partner_id
        cls.partner_employee.flush()

    @classmethod
    def _create_portal_user(cls):
        cls.user_portal = mail_new_test_user(
            cls.env, login='portal_test', groups='base.group_portal', company_id=cls.company_admin.id,
            name='Chell Gladys', notification_type='email')
        cls.partner_portal = cls.user_portal.partner_id
        return cls.user_portal
