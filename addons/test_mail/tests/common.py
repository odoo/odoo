# -*- coding: utf-8 -*-

import json
import time

from contextlib import contextmanager
from functools import partial

from odoo import api
from odoo.addons.bus.models.bus import json_dump
from odoo.tests import common, tagged, new_test_user
from odoo.tools import formataddr

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

        cls.user_employee = mail_new_test_user(cls.env, login='employee', groups='base.group_user', signature='--\nErnest', name='Ernest Employee')
        cls.partner_employee = cls.user_employee.partner_id

        cls.user_admin = cls.env.ref('base.user_admin')
        cls.partner_admin = cls.env.ref('base.partner_admin')

    @classmethod
    def _create_channel_listener(cls):
        cls.channel_listen = cls.env['mail.channel'].with_context(cls._test_context).create({'name': 'Listener'})

    @classmethod
    def _create_portal_user(cls):
        cls.user_portal = mail_new_test_user(cls.env, login='chell', groups='base.group_portal', name='Chell Gladys')
        cls.partner_portal = cls.user_portal.partner_id

    @classmethod
    def _create_template(cls, model, template_values=None):
        create_values = {
            'name': 'TestTemplate',
            'subject': 'About ${object.name}',
            'body_html': '<p>Hello ${object.name}</p>',
            'model_id': cls.env['ir.model']._get(model).id,
            'user_signature': False,
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

    @classmethod
    def _init_mail_gateway(cls):
        cls.alias_domain = 'test.com'
        cls.alias_catchall = 'catchall.test'
        cls.alias_bounce = 'bounce.test'
        cls.env['ir.config_parameter'].set_param('mail.bounce.alias', cls.alias_bounce)
        cls.env['ir.config_parameter'].set_param('mail.catchall.domain', cls.alias_domain)
        cls.env['ir.config_parameter'].set_param('mail.catchall.alias', cls.alias_catchall)

    @classmethod
    def _reset_mail_context(cls, record):
        return record.with_context(
            mail_create_nolog=False,
            mail_create_nosubscribe=False,
            mail_notrack=False
        )

    def _clear_bus(self):
        self.env['bus.bus'].search([]).unlink()

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
            if hasattr(self, '_init_mock_build_email'):
                self._init_mock_build_email()
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
                partner_notif = new_notifications.filtered(lambda n: n.res_partner_id == partner and (n.is_read == (notif_read not in ['unread', ''])))

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
                    self.assertTrue(all(n.notification_type == notif_type for n in partner_notif))
                    self.assertTrue(all(n.is_read == (notif_read == 'read') for n in partner_notif),
                                    'Invalid read status for %s' % partner.name)

            # for simplification, limitate to single message asserts
            if hasattr(self, 'assertEmails') and len(new_messages) == 1:
                self.assertEmails(new_messages.author_id, new_notifications.filtered(lambda n: n.notification_type == 'email').mapped('res_partner_id'))

    def assertBusNotification(self, channels, message_items=None, init=True):
        """ Check for bus notifications. Basic check is about used channels.
        Verifying content is optional.

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

    @contextmanager
    def sudo(self, login):
        old_uid = self.uid
        try:
            user = self.env['res.users'].sudo().search([('login', '=', login)])
            # switch user
            self.uid = user.id
            self.env = self.env(user=self.uid)
            yield
        finally:
            # back
            self.uid = old_uid
            self.env = self.env(user=self.uid)


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
            'email': 'valid.lelitre@agrolait.com',
            'country_id': cls.env.ref('base.be').id,
            'mobile': '0456001122',
        })
        cls.partner_2 = Partner.create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com',
            'country_id': cls.env.ref('base.be').id,
            'mobile': '+32 456 22 11 00',
        })


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
               extra='', email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>',
               cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>', **kwargs):
        return template.format(to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id, **kwargs)

    def format_and_process(self, template, email_from, to, subject='Frogs', extra='',  cc='', msg_id=False,
                           model=None, target_model='mail.test.gateway', target_field='name', **kwargs):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        if not msg_id:
            msg_id = "<%.7f-test@iron.sky>" % (time.time())

        mail = self.format(template, to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id, **kwargs)
        self.env['mail.thread'].with_context(mail_channel_noautofollow=True).message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])

    def gateway_reply_wrecord(self, template, record, use_in_reply_to=True):
        """ Simulate a reply through the mail gateway. Usage: giving a record,
        find an email sent to him and use its message-ID to simulate a reply.

        Some noise is added in References just to test some robustness. """
        email = self._find_sent_email_wrecord(record)

        if use_in_reply_to:
            extra = 'In-Reply-To:\r\n\t%s\n' % email['message_id']
        else:
            disturbing_other_msg_id = '<123456.654321@another.host.com>'
            extra = 'References:\r\n\t%s\n\r%s' % (email['message_id'], disturbing_other_msg_id)

        return self.format_and_process(
            template, email_from=email['email_to'][0], to=email['reply_to'],
            subject='Re: %s' % email['subject'],
            extra=extra,
            msg_id='<123456.%s.%d@test.example.com>' % (record._name, record.id),
            target_model=record._name,
            target_field=record._rec_name,
        )

    def _find_sent_email_wrecord(self, record):
        """ Helper to find in outgoing emails (see build_email) an email linked to
        a given record. It has been introduced with a fix for mass mailing and is
        not meant to be used widely, proper tools are available in later versions. """
        for mail in self._mails:
            if mail['object_id'] == '%d-%s' % (record.id, record._name):
                break
        else:
            raise AssertionError('Sent email not found for record %s' % record)
        return mail


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
