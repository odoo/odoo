# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import socket

from unittest.mock import DEFAULT
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.data import test_mail_data
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE
from odoo.addons.test_mail.models.test_mail_models import MailTestGateway
from odoo.addons.test_mail.tests.common import TestMailCommon
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import email_split_and_format, formataddr, mute_logger


@tagged('mail_gateway_custom')
class TestMailGatewayCustom(TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailGatewayCustom, cls).setUpClass()
        cls.test_model = cls.env['ir.model']._get('mail.gateway.custom')
        cls.email_from = '"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>'

        cls.gateway_custom = cls.env['mail.gateway.custom'].with_context(cls._test_context).create({
            'name': 'TestGatewayCustom',
        }).with_context({})

        cls.partner_1 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
        })
        # groups@.. will cause the creation of new mail.test.gateway
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'my.alias',
            'alias_user_id': False,
            'alias_model_id': cls.test_model.id,
            'alias_force_thread_id': cls.gateway_custom.id,
            'alias_contact': 'everyone'
        })

        # Set a first message on public group to test update and hierarchy
        cls.fake_email = cls.env['mail.gateway.message'].create({
            'subject': 'Public Discussion',
            'mail_gateway_id': cls.gateway_custom.id,
            'message_id': '<123456-openerp-%s-mail.gateway.custom@%s>' % (cls.gateway_custom.id, socket.gethostname()),
        })

        cls._init_mail_gateway()

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_message_process_alias_basic(self):
        """ Test details of created message going through mailgateway """
        gateway_custom = self.env['mail.gateway.custom'].browse(self.gateway_custom.ids)

        print(gateway_custom.custom_message_ids.subject)
        record = self.format_and_process(MAIL_TEMPLATE, self.email_from, 'my.alias@test.com', subject='Specific')

        # self.assertEqual(len(record), 0, 'message_process: update alias should not have create a new record')

        # Test: one message that is the incoming email
        
        print(gateway_custom.custom_message_ids.mapped('subject'))
