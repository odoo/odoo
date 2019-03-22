# -*- coding: utf-8 -*-

import json
import time

from contextlib import contextmanager
from email.utils import formataddr

from odoo.addons.mail.tests import common as mail_common
from odoo.tests import common, tagged


class BaseFunctionalTest(common.SavepointCase, mail_common.MailCase):

    _test_context = {
        'mail_create_nolog': True,
        'mail_create_nosubscribe': True,
        'mail_notrack': True,
        'no_reset_password': True
    }

    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()

        cls.user_employee = mail_common.mail_new_test_user(cls.env, login='employee', groups='base.group_user', signature='--\nErnest', name='Ernest Employee')
        cls.partner_employee = cls.user_employee.partner_id

        cls.user_admin = cls.env.ref('base.user_admin')
        cls.partner_admin = cls.env.ref('base.partner_admin')

    @classmethod
    def _create_channel_listener(cls):
        cls.channel_listen = cls.env['mail.channel'].with_context(cls._test_context).create({'name': 'Listener'})

    @classmethod
    def _create_portal_user(cls):
        cls.user_portal = mail_common.mail_new_test_user(cls.env, login='chell', groups='base.group_portal', name='Chell Gladys')
        cls.partner_portal = cls.user_portal.partner_id

    @classmethod
    def _init_mail_gateway(cls):
        cls.alias_domain = 'test.com'
        cls.alias_catchall = 'catchall.test'
        cls.alias_bounce = 'bounce.test'
        cls.env['ir.config_parameter'].set_param('mail.bounce.alias', cls.alias_bounce)
        cls.env['ir.config_parameter'].set_param('mail.catchall.domain', cls.alias_domain)
        cls.env['ir.config_parameter'].set_param('mail.catchall.alias', cls.alias_catchall)


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


@tagged('moderation')
class Moderation(mail_common.MockEmail, BaseFunctionalTest):

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

        cls.user_employee_2 = mail_common.mail_new_test_user(cls.env, login='roboute', groups='base.group_user', moderation_channel_ids=[(6, 0, [cls.channel_2.id])])
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
