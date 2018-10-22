# -*- coding: utf-8 -*-

import json

from contextlib import contextmanager
from email.utils import formataddr
from functools import partial

from odoo import api
from odoo.addons.bus.models.bus import json_dump
from odoo.tests import common, tagged, new_test_user

mail_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class BaseFunctionalTest(common.SavepointCase):

    _test_context = {
        'mail_create_nolog': True,
        'mail_create_nosubscribe': True,
        'mail_notrack': True,
        'no_reset_password': True
    }

    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()

        cls.user_employee = mail_new_test_user(cls.env, login='ernest', groups='base.group_user', signature='--\nErnest', name='Ernest Employee')
        cls.partner_employee = cls.user_employee.partner_id

        cls.user_admin = cls.env.ref('base.user_admin')
        cls.partner_admin = cls.env.ref('base.partner_admin')

        cls.channel_listen = cls.env['mail.channel'].with_context(cls._test_context).create({'name': 'Listener'})

        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

    @contextmanager
    def assertNotifications(self, **counters):
        """ Counters: 'partner_attribute': 'inbox' or 'email' """
        try:
            init = {}
            partners = self.env['res.partner']
            for partner_attribute in counters.keys():
                partners |= getattr(self, partner_attribute)
            init_notifs = self.env['mail.notification'].sudo().search([('res_partner_id', 'in', partners.ids)])
            for partner in partners:
                if partner.user_ids:
                    init[partner] = {
                        'na_counter': len([n for n in init_notifs if n.res_partner_id == partner and not n.is_read]),
                    }
            yield
        finally:
            new_notifications = self.env['mail.notification'].sudo().search([
                ('res_partner_id', 'in', partners.ids),
                ('id', 'not in', init_notifs.ids)
            ])
            new_messages = new_notifications.mapped('mail_message_id')

            for partner_attribute in counters.keys():
                counter, notif_type, notif_read = counters[partner_attribute]
                partner = getattr(self, partner_attribute)
                partner_notif = new_notifications.filtered(lambda n: n.res_partner_id == partner)

                self.assertEqual(len(partner_notif), counter)

                if partner.user_ids:
                    expected = init[partner]['na_counter'] + counter if notif_read == 'unread' else init[partner]['na_counter']
                    real = self.env['mail.notification'].sudo().search_count([
                        ('res_partner_id', '=', partner.id),
                        ('is_read', '=', False)
                    ])
                    self.assertEqual(expected, real, 'Invalid number of notification for %s: %s instead of %s' %
                                                     (partner.name, real, expected))
                if partner_notif:
                    self.assertTrue(all(n.is_email == (notif_type == 'email') for n in partner_notif))
                    self.assertTrue(all(n.is_read == (notif_read == 'read') for n in partner_notif),
                                    'Invalid read status for %s' % partner.name)

            # for simplification, limitate to single message asserts
            if hasattr(self, 'assertEmails') and len(new_messages) == 1:
                self.assertEmails(new_messages.author_id, new_notifications.filtered(lambda n: n.is_email).mapped('res_partner_id'))

    def assertBusNotification(self, channels, message_dicts=None, init=True):
        """ Check for bus notifications. Basic check is about used channels.
        Verifying content is optional.

        :param channels: list of channel
        :param messages: if given, list of message making a valid pair (channel,
          message) to be found in bus.bus
        """
        if init:
            self.assertEqual(len(self.env['bus.bus'].search([])), len(channels))
        notifications = self.env['bus.bus'].search([('channel', 'in', [json_dump(channel) for channel in channels])])
        self.assertEqual(len(notifications), len(channels))
        if message_dicts:
            notif_messages = [json.loads(n.message) for n in notifications]
            for expected in message_dicts:
                found = False
                for returned in notif_messages:
                    for key, val in expected.items():
                        if key not in returned:
                            continue
                        if isinstance(returned[key], list):
                            if set(returned[key]) != set(val):
                                continue
                        else:
                            if returned[key] != val:
                                continue
                            found = True
                            break
                    if found:
                        break
                if not found:
                    raise AssertionError("Bus notification content %s not found" % (repr(expected)))

    @contextmanager
    def sudoAs(self, login):
        old_uid = self.uid
        try:
            user = self.env['res.users'].sudo().search([('login', '=', login)])
            self.test_record_old = self.test_record
            # switch user
            self.uid = user.id
            self.env = self.env(user=self.uid)
            self.test_record = self.test_record.sudo(self.uid)
            yield
        finally:
            # back
            self.uid = old_uid
            self.env = self.env(user=self.uid)
            self.test_record = self.test_record_old


class TestRecipients(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestRecipients, cls).setUpClass()
        Partner = cls.env['res.partner'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
            'no_reset_password': True,
        })
        cls.partner_1 = Partner.create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com'})
        cls.partner_2 = Partner.create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com'})


class MockEmails(common.SingleTransactionCase):

    def setUp(self):
        super(MockEmails, self).setUp()
        self._mails_args[:] = []
        self._mails[:] = []

    @classmethod
    def setUpClass(cls):
        super(MockEmails, cls).setUpClass()
        cls._mails_args = []
        cls._mails = []

        def build_email(self, *args, **kwargs):
            cls._mails_args.append(args)
            cls._mails.append(kwargs)
            return build_email.origin(self, *args, **kwargs)

        @api.model
        def send_email(self, message, *args, **kwargs):
            return message['Message-Id']

        cls.env['ir.mail_server']._patch_method('build_email', build_email)
        cls.env['ir.mail_server']._patch_method('send_email', send_email)

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

    @classmethod
    def tearDownClass(cls):
        # Remove mocks
        cls.env['ir.mail_server']._revert_method('build_email')
        cls.env['ir.mail_server']._revert_method('send_email')
        super(MockEmails, cls).tearDownClass()

    def _init_mock_build_email(self):
        self.env['mail.mail'].search([]).unlink()
        self._mails_args[:] = []
        self._mails[:] = []

    def format(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
               extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
               cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>'):
        return template.format(to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)

    def format_and_process(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
                           extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
                           cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>',
                           model=None, target_model='mail.test.simple', target_field='name'):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        mail = self.format(template, to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)
        self.env['mail.thread'].with_context(mail_channel_noautofollow=True).message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])


@tagged('moderation')
class Moderation(MockEmails, BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(Moderation, cls).setUpClass()
        Channel = cls.env['mail.channel']

        cls.channel_moderation_1 = Channel.create({
            'name': 'Moderation_1',
            'email_send': True,
            'moderation': True
            })
        cls.channel_1 = cls.channel_moderation_1
        cls.channel_moderation_2 = Channel.create({
            'name': 'Moderation_2',
            'email_send': True,
            'moderation': True
            })
        cls.channel_2 = cls.channel_moderation_2

        cls.user_employee.write({'moderation_channel_ids': [(6, 0, [cls.channel_1.id])]})

        cls.user_employee_2 = mail_new_test_user(cls.env, login='roboute', groups='base.group_user', moderation_channel_ids=[(6, 0, [cls.channel_2.id])])
        cls.partner_employee_2 = cls.user_employee_2.partner_id

        cls.channel_moderation_1.write({'channel_last_seen_partner_ids': [(0, 0, {'partner_id': cls.partner_employee.id})]})
        cls.channel_moderation_2.write({'channel_last_seen_partner_ids': [(0, 0, {'partner_id': cls.partner_employee_2.id})]})

    def _create_new_message(self, channel_id, status='pending_moderation', author=None, body='', message_type="email"):
        author = author if author else self.env.user.partner_id
        message = self.env['mail.message'].create({
            'model': 'mail.channel',
            'res_id': channel_id,
            'message_type': 'email',
            'body': body,
            'moderation_status': status,
            'author_id': author.id,
            'email_from': formataddr((author.name, author.email)),
            'subtype_id': self.env['mail.message.subtype'].search([('name', '=', 'Discussions')]).id
            })
        return message

    def _clear_bus(self):
        self.env['bus.bus'].search([]).unlink()
