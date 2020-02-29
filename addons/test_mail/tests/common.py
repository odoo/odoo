# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests import common as mail_common
from odoo.tests import common

mail_new_test_user = mail_common.mail_new_test_user


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
        }
        if template_values:
            create_values.update(template_values)
        cls.email_template = cls.env['mail.template'].create(create_values)
        return cls.email_template

    def flush_tracking(self):
        """ Force the creation of tracking values. """
        self.env['base'].flush()
        self.cr.precommit()


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
