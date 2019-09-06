# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.test_mail.tests.common import BaseFunctionalTest, MockEmails, TestRecipients
from odoo.addons.test_mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.models.test_mail_models import MailTestSimple
from odoo.tools import mute_logger


class TestComposer(BaseFunctionalTest, MockEmails, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestComposer, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        # configure mailing
        cls.alias_domain = 'schlouby.fr'
        cls.alias_catchall = 'test+catchall'
        cls.env['ir.config_parameter'].set_param('mail.catchall.domain', cls.alias_domain)
        cls.env['ir.config_parameter'].set_param('mail.catchall.alias', cls.alias_catchall)

        # admin should not receive emails
        cls.user_admin.write({'notification_type': 'email'})

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_comment(self):
        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': self.test_record._name,
            'default_res_id': self.test_record.id,
        }).with_user(self.user_employee).create({
            'body': '<p>Test Body</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        composer.send_mail()

        message = self.test_record.message_ids[0]
        self.assertEqual(message.body, '<p>Test Body</p>')
        self.assertEqual(message.author_id, self.user_employee.partner_id)
        self.assertEqual(message.subject, 'Re: %s' % self.test_record.name)
        self.assertEqual(message.subtype_id, self.env.ref('mail.mt_comment'))
        self.assertEqual(message.partner_ids, self.partner_1 | self.partner_2)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_comment_parent(self):
        parent = self.test_record.message_post(body='Test')

        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_parent_id': parent.id
        }).with_user(self.user_employee).create({
            'body': '<p>Mega</p>',
        }).send_mail()

        message = self.test_record.message_ids[0]
        self.assertEqual(message.body, '<p>Mega</p>')
        self.assertEqual(message.parent_id, parent)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_mass_mail(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test2'})

        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': self.test_record._name,
            'default_res_id': False,
            'active_ids': [self.test_record.id, test_record_2.id]
        }).with_user(self.user_employee).create({
            'subject': 'Testing ${object.name}',
            'body': '<p>${object.name}</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        composer.with_context({
            'default_res_id': -1,
            'active_ids': [self.test_record.id, test_record_2.id]
        }).send_mail()

        # check mail_mail
        mails = self.env['mail.mail'].search([('subject', 'ilike', 'Testing')])
        for mail in mails:
            self.assertEqual(mail.recipient_ids, self.partner_1 | self.partner_2,
                             'compose wizard: mail_mail mass mailing: mail.mail in mass mail incorrect recipients')

        # check message on test_record
        message1 = self.test_record.message_ids[0]
        self.assertEqual(message1.subject, 'Testing %s' % self.test_record.name)
        self.assertEqual(message1.body, '<p>%s</p>' % self.test_record.name)

        # check message on test_record_2
        message1 = test_record_2.message_ids[0]
        self.assertEqual(message1.subject, 'Testing %s' % test_record_2.name)
        self.assertEqual(message1.body, '<p>%s</p>' % test_record_2.name)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_mass_mail_active_domain(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test2'})

        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': self.test_record._name,
            'default_use_active_domain': True,
            'active_ids': [self.test_record.id],
            'active_domain': [('name', 'in', ['%s' % self.test_record.name, '%s' % test_record_2.name])],
        }).with_user(self.user_employee).create({
            'subject': 'From Composer Test',
            'body': '${object.name}',
        }).send_mail()

        self.assertEqual(self.test_record.message_ids[0].subject, 'From Composer Test')
        self.assertEqual(test_record_2.message_ids[0].subject, 'From Composer Test')

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose_mass_mail_no_active_domain(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._test_context).create({'name': 'Test2'})

        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': self.test_record._name,
            'default_use_active_domain': False,
            'active_ids': [self.test_record.id],
            'active_domain': [('name', 'in', ['%s' % self.test_record.name, '%s' % test_record_2.name])],
        }).with_user(self.user_employee).create({
            'subject': 'From Composer Test',
            'body': '${object.name}',
        }).send_mail()

        self.assertEqual(self.test_record.message_ids[0].subject, 'From Composer Test')
        self.assertFalse(test_record_2.message_ids.ids)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose_portal_ok(self):
        portal_user = mail_new_test_user(self.env, login='chell', groups='base.group_portal', name='Chell Gladys')

        with patch.object(MailTestSimple, 'check_access_rights', return_value=True):
            ComposerPortal = self.env['mail.compose.message'].with_user(portal_user)

            ComposerPortal.with_context({
                'default_composition_mode': 'comment',
                'default_model': self.test_record._name,
                'default_res_id': self.test_record.id,
            }).create({
                'subject': 'Subject',
                'body': '<p>Body text</p>',
                'partner_ids': []}).send_mail()

            self.assertEqual(self.test_record.message_ids[0].body, '<p>Body text</p>')
            self.assertEqual(self.test_record.message_ids[0].author_id, portal_user.partner_id)

            ComposerPortal.with_context({
                'default_composition_mode': 'comment',
                'default_parent_id': self.test_record.message_ids.ids[0],
            }).create({
                'subject': 'Subject',
                'body': '<p>Body text 2</p>'}).send_mail()

            self.assertEqual(self.test_record.message_ids[0].body, '<p>Body text 2</p>')
            self.assertEqual(self.test_record.message_ids[0].author_id, portal_user.partner_id)
