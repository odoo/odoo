# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests import common as mail_common
from odoo.tests import common

<<<<<<< HEAD
mail_new_test_user = mail_common.mail_new_test_user

=======
from contextlib import contextmanager
from functools import partial

from odoo import api
from odoo.addons.bus.models.bus import json_dump
from odoo.tests import common, tagged, new_test_user
from odoo.tools import formataddr
>>>>>>> 42347b86f35... temp

class TestMailCommon(common.SavepointCase, mail_common.MailCase):

    @classmethod
    def setUpClass(cls):
        super(TestMailCommon, cls).setUpClass()
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
            cls.env, login='employee', groups='base.group_user', company_id=cls.company_admin.id,
            name='Ernest Employee', notification_type='inbox', signature='--\nErnest')
        cls.partner_employee = cls.user_employee.partner_id

    @classmethod
    def _create_channel_listener(cls):
        cls.channel_listen = cls.env['mail.channel'].with_context(cls._test_context).create({'name': 'Listener'})

    @classmethod
    def _create_portal_user(cls):
        cls.user_portal = mail_new_test_user(
            cls.env, login='portal_test', groups='base.group_portal', company_id=cls.company_admin.id,
            name='Chell Gladys', notification_type='email')
        cls.partner_portal = cls.user_portal.partner_id
        return cls.user_portal

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


class TestMailMultiCompanyCommon(TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailMultiCompanyCommon, cls).setUpClass()
        cls.company_2 = cls.env['res.company'].create({
            'name': 'Second Test Company',
        })


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
<<<<<<< HEAD
=======


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
>>>>>>> 42347b86f35... temp
