# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import email
import email.policy
import time

from collections import defaultdict
from contextlib import contextmanager
from functools import partial
from lxml import html
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

    # ------------------------------------------------------------
    # GATEWAY MOCK
    # ------------------------------------------------------------

    @contextmanager
    def mock_mail_gateway(self, mail_unlink_sent=False, sim_error=None):
        build_email_origin = IrMailServer.build_email
        mail_create_origin = MailMail.create
        mail_unlink_origin = MailMail.unlink
        self.mail_unlink_sent = mail_unlink_sent
        self._init_mail_mock()

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
               extra='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
               **kwargs):
        return template.format(
            subject=subject, to=to, cc=cc,
            email_from=email_from, return_path=return_path,
            extra=extra, msg_id=msg_id,
            **kwargs)

    def format_and_process(self, template, email_from, to, subject='Frogs', cc='',
                           return_path='', extra='',  msg_id=False,
                           model=None, target_model='mail.test.gateway', target_field='name',
                           **kwargs):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        if not msg_id:
            msg_id = "<%.7f-test@iron.sky>" % (time.time())

        mail = self.format(template, to=to, subject=subject, cc=cc,
                           return_path=return_path, extra=extra,
                           email_from=email_from, msg_id=msg_id,
                           **kwargs)
        self.env['mail.thread'].with_context(mail_channel_noautofollow=True).message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])

    def gateway_reply_wrecord(self, template, record, use_in_reply_to=True):
        """ Deprecated, remove in 14.4 """
        return self.gateway_mail_reply_wrecord(template, record, use_in_reply_to=use_in_reply_to)

    def gateway_mail_reply_wrecord(self, template, record, use_in_reply_to=True,
                                   target_model=None, target_field=None):
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
            target_model=target_model or record._name,
            target_field=target_field or record._rec_name,
        )

    def gateway_mail_reply_wemail(self, template, email_to, use_in_reply_to=True,
                                  target_model=None, target_field=None):
        """ Simulate a reply through the mail gateway. Usage: giving a record,
        find an email sent to him and use its message-ID to simulate a reply.

        Some noise is added in References just to test some robustness. """
        sent_mail = self._find_sent_mail_wemail(email_to)

        if use_in_reply_to:
            extra = 'In-Reply-To:\r\n\t%s\n' % sent_mail['message_id']
        else:
            disturbing_other_msg_id = '<123456.654321@another.host.com>'
            extra = 'References:\r\n\t%s\n\r%s' % (sent_mail['message_id'], disturbing_other_msg_id)

        return self.format_and_process(
            template,
            sent_mail['email_to'],
            sent_mail['reply_to'],
            subject='Re: %s' % sent_mail['subject'],
            extra=extra,
            target_model=target_model,
            target_field=target_field or 'name',
        )

    def from_string(self, text):
        return email.message_from_string(pycompat.to_text(text), policy=email.policy.SMTP)

    def assertHtmlEqual(self, value, expected, message=None):
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
    # GATEWAY GETTERS
    # ------------------------------------------------------------

    def _find_sent_mail_wemail(self, email_to):
        """ Find a sent email with a given list of recipients. Email should match
        exactly the recipients.

        :param email-to: a list of emails that will be compared to email_to
          of sent emails (also a list of emails);

        :return email: an email which is a dictionary mapping values given to
          ``build_email``;
        """
        for sent_email in self._mails:
            if set(sent_email['email_to']) == set([email_to]):
                break
        else:
            raise AssertionError('sent mail not found for email_to %s' % (email_to))
        return sent_email

    def _filter_mail(self, status=None, mail_message=None, author=None):
        """ Filter mail generated during mock, based on common parameters

        :param status: state of mail.mail. If not void use it to filter mail.mail
          record;
        :param mail_message: optional check/filter on mail_message_id field aka
          a ``mail.message`` record;
        :param author: optional check/filter on author_id field aka a ``res.partner``
          record;
        """
        filtered = self._new_mails.env['mail.mail']
        for mail in self._new_mails:
            if status is not None and mail.state != status:
                continue
            if mail_message is not None and mail.mail_message_id != mail_message:
                continue
            if author is not None and mail.author_id != author:
                continue
            filtered += mail
        return filtered

    def _find_mail_mail_wid(self, mail_id, status=None, mail_message=None, author=None):
        """ Find a ``mail.mail`` record based on a given ID (used notably when having
        mail ID in mailing traces).

        :return mail: a ``mail.mail`` record generated during the mock and matching
          given ID;
        """
        filtered = self._filter_mail(status=status, mail_message=mail_message, author=author)
        for mail in filtered:
            if mail.id == mail_id:
                break
        else:
            raise AssertionError('mail.mail not found for ID %s' % (mail_id))
        return mail

    def _find_mail_mail_wpartners(self, recipients, status, mail_message=None, author=None):
        """ Find a mail.mail record based on various parameters, notably a list
        of recipients (partners).

        :param recipients: a ``res.partner`` recordset Check all of them are in mail
          recipients to find the right mail.mail record;

        :return mail: a ``mail.mail`` record generated during the mock and matching
          given parameters and filters;
        """
        filtered = self._filter_mail(status=status, mail_message=mail_message, author=author)
        for mail in filtered:
            if all(p in mail.recipient_ids for p in recipients):
                break
        else:
            raise AssertionError('mail.mail not found for message %s / status %s / recipients %s / author %s' % (mail_message, status, recipients.ids, author))
        return mail

    def _find_mail_mail_wemail(self, email_to, status, mail_message=None, author=None):
        """ Find a mail.mail record based on various parameters, notably a list
        of email to (string emails).

        :param email_to: either matching mail.email_to value, either a mail sent
          to a single recipient whose email is email_to;

        :return mail: a ``mail.mail`` record generated during the mock and matching
          given parameters and filters;
        """
        filtered = self._filter_mail(status=status, mail_message=mail_message, author=author)
        for mail in filtered:
            if (mail.email_to == email_to and not mail.recipient_ids) or (not mail.email_to and mail.recipient_ids.email == email_to):
                break
        else:
            raise AssertionError('mail.mail not found for email_to %s / status %s in %s' % (email_to, status, repr([m.email_to for m in self._new_mails])))
        return mail

    def _find_mail_mail_wrecord(self, record, status=None, mail_message=None, author=None):
        """ Find a mail.mail record based on model / res_id of a record.

        :return mail: a ``mail.mail`` record generated during the mock;
        """
        filtered = self._filter_mail(status=status, mail_message=mail_message, author=author)
        for mail in filtered:
            if mail.model == record._name and mail.res_id == record.id:
                break
        else:
            raise AssertionError('mail.mail not found for record %s in %s' % (record, repr([m.email_to for m in self._new_mails])))
        return mail

    # ------------------------------------------------------------
    # GATEWAY ASSERTS
    # ------------------------------------------------------------

    def assertMailMail(self, recipients, status,
                       check_mail_mail=True, mail_message=None, author=None,
                       content=None, fields_values=None, email_values=None):
        """ Assert mail.mail records are created and maybe sent as emails. Allow
        asserting their content. Records to check are the one generated when
        using mock (mail.mail and outgoing emails). This method takes partners
        as source of record fetch and assert.

        :param recipients: a ``res.partner`` recordset. See ``_find_mail_mail_wpartners``;
        :param status: mail.mail state used to filter mails. If ``sent`` this method
          also check that emails have been sent trough gateway;
        :param mail_message: see ``_find_mail_mail_wpartners``;
        :param author: see ``_find_mail_mail_wpartners``;
        :param content: if given, check it is contained within mail html body;
        :param fields_values: if given, should be a dictionary of field names /
          values allowing to check ``mail.mail`` additional values (subject,
          reply_to, ...);
        :param email_values: if given, should be a dictionary of keys / values
          allowing to check sent email additional values (if any).
          See ``assertSentEmail``;

        :param check_mail_mail: deprecated, use ``assertSentEmail`` if False
        """
        found_mail = self._find_mail_mail_wpartners(recipients, status, mail_message=mail_message, author=author)
        self.assertTrue(bool(found_mail))
        if content:
            self.assertIn(content, found_mail.body_html)
        for fname, fvalue in (fields_values or {}).items():
            self.assertEqual(
                found_mail[fname], fvalue,
                'Mail: expected %s for %s, got %s' % (fvalue, fname, found_mail[fname]))
        if status == 'sent':
            for recipient in recipients:
                self.assertSentEmail(email_values['email_from'] if email_values and email_values.get('email_from') else author, [recipient], **(email_values or {}))

    def assertMailMailWEmails(self, emails, status,
                              mail_message=None, author=None,
                              content=None, fields_values=None, email_values=None):
        """ Assert mail.mail records are created and maybe sent as emails. Allow
        asserting their content. Records to check are the one generated when
        using mock (mail.mail and outgoing emails). This method takes emails
        as source of record fetch and assert.

        :param emails: a list of emails. See ``_find_mail_mail_wemail``;
        :param status: mail.mail state used to filter mails. If ``sent`` this method
          also check that emails have been sent trough gateway;
        :param mail_message: see ``_find_mail_mail_wemail``;
        :param author: see ``_find_mail_mail_wemail``;;
        :param content: if given, check it is contained within mail html body;
        :param fields_values: if given, should be a dictionary of field names /
          values allowing to check ``mail.mail`` additional values (subject,
          reply_to, ...);
        :param email_values: if given, should be a dictionary of keys / values
          allowing to check sent email additional values (if any).
          See ``assertSentEmail``;

        :param check_mail_mail: deprecated, use ``assertSentEmail`` if False
        """
        for email_to in emails:
            found_mail = self._find_mail_mail_wemail(email_to, status, mail_message=mail_message, author=author)
            if content:
                self.assertIn(content, found_mail.body_html)
            for fname, fvalue in (fields_values or {}).items():
                self.assertEqual(
                    found_mail[fname], fvalue,
                    'Mail: expected %s for %s, got %s' % (fvalue, fname, found_mail[fname]))
        if status == 'sent':
            for email_to in emails:
                self.assertSentEmail(email_values['email_from'] if email_values and email_values.get('email_from') else author, [email_to], **(email_values or {}))

    def assertMailMailWId(self, mail_id, status,
                          content=None, fields_values=None):
        """ Assert mail.mail records are created and maybe sent as emails. Allow
        asserting their content. Records to check are the one generated when
        using mock (mail.mail and outgoing emails). This method takes partners
        as source of record fetch and assert.

        :param mail_id: a ``mail.mail`` DB ID. See ``_find_mail_mail_wid``;
        :param status: mail.mail state to check upon found mail;
        :param content: if given, check it is contained within mail html body;
        :param fields_values: if given, should be a dictionary of field names /
          values allowing to check ``mail.mail`` additional values (subject,
          reply_to, ...);
        """
        found_mail = self._find_mail_mail_wid(mail_id)
        self.assertTrue(bool(found_mail))
        if status:
            self.assertEqual(found_mail.state, status)
        if content:
            self.assertIn(content, found_mail.body_html)
        for fname, fvalue in (fields_values or {}).items():
            self.assertEqual(
                found_mail[fname], fvalue,
                'Mail: expected %s for %s, got %s' % (fvalue, fname, found_mail[fname]))

    def assertNoMail(self, recipients, mail_message=None, author=None):
        """ Check no mail.mail and email was generated during gateway mock. """
        try:
            self._find_mail_mail_wpartners(recipients, False, mail_message=mail_message, author=author)
        except AssertionError:
            pass
        else:
            raise AssertionError('mail.mail exists for message %s / recipients %s but should not exist' % (mail_message, recipients.ids))
        finally:
            self.assertNotSentEmail(recipients)

    def assertNotSentEmail(self, recipients=None):
        """Check no email was generated during gateway mock.

        :param recipients:
            List of partner for which we will check that no email have been sent
            Or list of email address
            If None, we will check that no email at all have been sent
        """
        if recipients is None:
            mails = self._mails
        else:
            all_emails = [
                email_to.email if isinstance(email_to, self.env['res.partner'].__class__)
                else email_to
                for email_to in recipients
            ]

            mails = [
                mail
                for mail in self._mails
                if any(email in all_emails for email in mail['email_to'])
            ]

        self.assertEqual(len(mails), 0)

    def assertSentEmail(self, author, recipients, **values):
        """ Tool method to ease the check of send emails.

        :param author: email author, either a string (email), either a partner
          record;
        :param recipients: list of recipients, each being either a string (email),
          either a partner record;
        :param values: dictionary of additional values to check email content;
        """
        direct_check = ['attachments', 'body_alternative', 'email_from', 'references', 'reply_to', 'subject']
        content_check = ['body_alternative_content', 'body_content', 'references_content']
        other_check = ['body', 'attachments_info']

        expected = {}
        for fname in direct_check + content_check + other_check:
            if fname in values:
                expected[fname] = values[fname]
        unknown = set(values.keys()) - set(direct_check + content_check + other_check)
        if unknown:
            raise NotImplementedError('Unsupported %s' % ', '.join(unknown))

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

        for val in direct_check:
            if val in expected:
                self.assertEqual(expected[val], sent_mail[val], 'Value for %s: expected %s, received %s' % (val, expected[val], sent_mail[val]))
        if 'attachments_info' in expected:
            attachments = sent_mail['attachments']
            for attachment_info in expected['attachments_info']:
                attachment = next(attach for attach in attachments if attach[0] == attachment_info['name'])
                if attachment_info.get('raw'):
                    self.assertEqual(attachment[1], attachment_info['raw'])
                if attachment_info.get('type'):
                    self.assertEqual(attachment[2], attachment_info['type'])
            self.assertEqual(len(expected['attachments_info']), len(attachments))
        if 'body' in expected:
            self.assertHtmlEqual(expected['body'], sent_mail['body'], 'Value for %s: expected %s, received %s' % ('body', expected['body'], sent_mail['body']))
        for val in content_check:
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
            mail_groups = {'failure': [], 'outgoing': []}
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
                    # when force_send is False notably, notifications are ready and emails outgoing
                    elif nstatus == 'ready':
                        mail_groups['outgoing'].append(partner)
                        if ncheck_send:
                            email_groups[ngroup].append(partner)
                    # canceled: currently nothing checked
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
            email_values = {'body_content': mbody,
                            'references_content': message.message_id}
            if message_info.get('email_values'):
                email_values.update(message_info['email_values'])
            for recipients in email_groups.values():
                partners = self.env['res.partner'].sudo().concat(*recipients)
                if all(p in mail_groups['failure'] for p in partners):
                    mail_status = 'exception'
                elif all(p in mail_groups['outgoing'] for p in partners):
                    mail_status = 'outgoing'
                else:
                    mail_status = 'sent'
                if not self.mail_unlink_sent:
                    self.assertMailMail(
                        partners, mail_status,
                        author=message.author_id if message.author_id else message.email_from,
                        mail_message=message,
                        email_values=email_values,
                    )
                else:
                    for recipient in partners:
                        self.assertSentEmail(
                            message.author_id if message.author_id else message.email_from,
                            [recipient],
                            **email_values
                        )

            if not any(p for recipients in email_groups.values() for p in recipients):
                self.assertNoMail(partners, mail_message=message, author=message.author_id)

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

    def assertNotified(self, message, recipients_info, is_complete=False):
        """ Lightweight check for notifications (mail.notification).

        :param recipients_info: list notified recipients: [
          {'partner': res.partner record (may be empty),
           'type': notification_type to check,
           'is_read': is_read to check,
          }, {...}]
        """
        notifications = self._new_notifs.filtered(lambda notif: notif in message.notification_ids)
        if is_complete:
            self.assertEqual(len(notifications), len(recipients_info))
        for rinfo in recipients_info:
            recipient_notif = next(
                (notif
                 for notif in notifications
                 if notif.res_partner_id == rinfo['partner']
                ), False
            )
            self.assertTrue(recipient_notif)
            self.assertEqual(recipient_notif.is_read, rinfo['is_read'])
            self.assertEqual(recipient_notif.notification_type, rinfo['type'])

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

    @classmethod
    def _activate_multi_company(cls):
        """ Create another company, add it to admin and create an user that
        belongs to that new company. It allows to test flows with users from
        different companies. """
        cls.company_2 = cls.env['res.company'].create({
            'name': 'Company 2',
            'email': 'company_2@test.example.com',
        })
        cls.user_admin.write({'company_ids': [(4, cls.company_2.id)]})

        cls.user_employee_c2 = mail_new_test_user(
            cls.env, login='employee_c2',
            groups='base.group_user',
            company_id=cls.company_2.id,
            company_ids=[(4, cls.company_2.id)],
            name='Enguerrand Employee C2',
            notification_type='inbox',
            signature='--\nEnguerrand'
        )
        cls.partner_employee_c2 = cls.user_employee_c2.partner_id
