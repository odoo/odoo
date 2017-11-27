# -*- coding: utf-8 -*-

from contextlib import contextmanager
from email.utils import formataddr

from odoo import api
from odoo.tests import common


class BaseFunctionalTest(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()
        cls._quick_create_ctx = {
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
        }
        cls._quick_create_user_ctx = dict(cls._quick_create_ctx, no_reset_password=True)

        user_group_employee = cls.env.ref('base.group_user')
        cls.user_employee = cls.env['res.users'].with_context(cls._quick_create_user_ctx).create({
            'name': 'Ernest Employee',
            'login': 'ernest',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notification_type': 'email',
            'groups_id': [(6, 0, [user_group_employee.id])]})
        cls.partner_employee = cls.user_employee.partner_id
        cls.user_admin = cls.env.user
        cls.partner_admin = cls.user_admin.partner_id

        cls.channel_listen = cls.env['mail.channel'].with_context(cls._quick_create_ctx).create({'name': 'Listener'})

        cls.test_record = cls.env['mail.test.simple'].with_context(cls._quick_create_ctx).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

    @contextmanager
    def assertNotifications(self, **counters):
        """ Counters: 'partner_attribute': 'inbox' or 'email' """
        try:
            init_messages = self.test_record.message_ids
            init = {}
            partners = self.env['res.partner']
            for partner_attribute in counters.keys():
                partner = getattr(self, partner_attribute)
                partners |= partner
                if partner.user_ids:
                    init[partner] = {
                        'na_counter': self.test_record.sudo(partner.user_ids[0]).message_needaction_counter,
                    }
            yield
        finally:
            new_messages = self.test_record.sudo().message_ids - init_messages
            new_notifications = self.env['mail.notification'].search([
                ('res_partner_id', 'in', partners.ids),
                ('mail_message_id', 'in', new_messages.ids)
            ])

            for partner_attribute in counters.keys():
                counter, notif_type, notif_read = counters[partner_attribute]
                partner = getattr(self, partner_attribute)
                partner_notif = new_notifications.filtered(lambda n: n.res_partner_id == partner)

                self.assertEqual(len(partner_notif), counter)

                if partner.user_ids:
                    expected = init[partner]['na_counter'] + counter if notif_read == 'unread' else init[partner]['na_counter']
                    self.assertEqual(expected, self.test_record.sudo(partner.user_ids[0]).message_needaction_counter,
                                     'Invalid number of notification for %s: %s instead of %s' %
                                     (partner.name, expected, self.test_record.sudo(partner.user_ids[0]).message_needaction_counter))
                if partner_notif:
                    self.assertTrue(all(n.is_email == (notif_type == 'email') for n in partner_notif))
                    self.assertTrue(all(n.is_read == (notif_read == 'read') for n in partner_notif),
                                    'Invalid read status for %s' % partner.name)

            # for simplification, limitate to single message asserts
            if hasattr(self, 'assertEmails') and len(new_messages) == 1:
                self.assertEmails(new_messages.author_id, new_notifications.filtered(lambda n: n.is_email).mapped('res_partner_id'))

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
            expected = {
                'email_from': formataddr((partner_from.name, partner_from.email)),
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
