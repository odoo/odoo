# -*- coding: utf-8 -*-

from contextlib import contextmanager
from email.utils import formataddr
from functools import partial
from unittest.mock import patch

from odoo.addons.base.models.ir_mail_server import IrMailServer
from odoo.tests import common, new_test_user

mail_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class MockEmail(common.BaseCase):

    @contextmanager
    def mockGateway(self):
        self._mails = []
        self._mail_args = []

        def _build_email(self, *args, **kwargs):
            print('building', args, kwargs)
            self._mails.append(kwargs)
            self._mail_args.append(args)

        def _send_email(self, message, *args, **kwargs):
            print('sending', message['Message-Id'])
            return message['Message-Id']

        try:
            with patch.object(IrMailServer, 'connect', return_value=True), \
                    patch.object(IrMailServer, 'build_email', side_effect=_build_email) as build_email_method_mock, \
                    patch.object(IrMailServer, 'send_email', side_effect=_send_email):
                yield
        finally:
            pass

    def assertEmails(self, partner_from, recipients, **values):
        """ Tools method to ease the check of send emails """
        expected_email_values = []
        for partners in recipients:
            if partner_from:
                email_from = formataddr((partner_from.name, partner_from.email))
            else:
                email_from = values['email_from']
            expected = {
                'email_from': email_from,
                'email_to': [formataddr((partner.name, partner.email)) for partner in partners]
            }
            if 'reply_to' in values:
                expected['reply_to'] = values['reply_to']
            if 'subject' in values:
                expected['subject'] = values['subject']
            if 'attachments' in values:
                expected['attachments'] = values['attachments']
            if 'body' in values:
                expected['body'] = values['body']
            if 'body_content' in values:
                expected['body_content'] = values['body_content']
            if 'body_alt_content' in values:
                expected['body_alternative_content'] = values['body_alt_content']
            if 'references' in values:
                expected['references'] = values['references']
            if 'ref_content' in values:
                expected['references_content'] = values['ref_content']
            expected_email_values.append(expected)

        self.assertEqual(len(self._mails), len(expected_email_values))
        for expected in expected_email_values:
            sent_mail = next((mail for mail in self._mails if set(mail['email_to']) == set(expected['email_to'])), False)
            self.assertTrue(bool(sent_mail), 'Expected mail to %s not found' % expected['email_to'])
            for val in ['email_from', 'reply_to', 'subject', 'body', 'references', 'attachments']:
                if val in expected:
                    self.assertEqual(expected[val], sent_mail[val], 'Value for %s: expected %s, received %s' % (val, expected[val], sent_mail[val]))
            for val in ['body_content', 'body_alternative', 'references_content']:
                if val in expected:
                    self.assertIn(expected[val], sent_mail[val[:-8]], 'Value for %s: %s does not contain %s' % (val, sent_mail[val[:-8]], expected[val]))

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

    def format(self, template, subject, to, email_from,
               cc='', extra='', msg_id='<123.456.789.JavaMail@agrolait.com>'):
        return template.format(subject=subject, email_from=email_from, to=to, cc=cc, extra=extra, msg_id=msg_id)

    def format_and_process(self, template, subject, to, email_from,
                           cc='', extra='', msg_id='<123.456.789.JavaMail@agrolait.com>',
                           model=None, target_model='mail.test.simple', target_field='name'):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        mail = self.format(template, to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)
        self.env['mail.thread'].with_context(mail_channel_noautofollow=True).message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])
