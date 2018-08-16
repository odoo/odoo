# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from unittest.mock import patch

from odoo.addons.test_mail.tests import common
from odoo.tests import tagged
from odoo.tools import mute_logger
from odoo import api
from odoo.addons.base.models.ir_mail_server import IrMailServer


@tagged('resend_test')
class TestMailResend(common.BaseFunctionalTest, common.MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestMailResend, cls).setUpClass()
        #Two users
        cls.user1 = cls.env['res.users'].with_context(cls._quick_create_user_ctx).create({
            'name': 'Employee 1',
            'login': 'e1',
            'email': 'e1',  # invalid email
            'notification_type': 'email',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        cls.user2 = cls.env['res.users'].with_context(cls._quick_create_user_ctx).create({
            'name': 'Employee 2',
            'login': 'e2',
            'email': 'e2@example.com',
            'notification_type': 'email',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        #Two partner
        cls.partner1 = cls.env['res.partner'].with_context(cls._quick_create_user_ctx).create({
            'name': 'Partner 1',
            'email': 'p1'  # invalid email
        })
        cls.partner2 = cls.env['res.partner'].with_context(cls._quick_create_user_ctx).create({
            'name': 'Partner 2',
            'email': 'p2@example.com'
        })

        @api.model
        def send_email(self, message, *args, **kwargs):
            assert '@' in message['To'], self.NO_VALID_RECIPIENT
            return message['Message-Id']
        cls.bus_update_failure = []
        def sendone(self, channel, message):
            if 'type' in message and message['type'] == 'mail_failure':
                cls.bus_update_failure.append((channel, message))
        cls.env['ir.mail_server']._patch_method('send_email', send_email)
        cls.env['bus.bus']._patch_method('sendone', sendone)
        cls.partners = cls.env['res.partner'].concat(cls.user1.partner_id, cls.user2.partner_id, cls.partner1, cls.partner2)
        cls.invalid_email_partners = cls.env['res.partner'].concat(cls.user1.partner_id, cls.partner1)

    def setUp(self):
        super(TestMailResend, self).setUp()
        TestMailResend.bus_update_failure = []

    def assertNotifStates(self, states, message):
        notif = self.env['mail.notification'].search([('mail_message_id', '=', message.id)], order="res_partner_id asc")
        self.assertEquals(tuple(notif.mapped('email_status')), states)
        return notif

    def assertBusMessage(self, partners):
        partner_ids = [elem[0][2] for elem in self.bus_update_failure]
        self.assertEquals(partner_ids, [partner.id for partner in partners])
        self.bus_update_failure.clear()

    @classmethod
    def tearDownClass(cls):
        # Remove mocks
        cls.env['ir.mail_server']._revert_method('send_email')
        cls.env['bus.bus']._revert_method('sendone')
        super(TestMailResend, cls).tearDownClass()

    def assertEmails(self, *args, **kwargs):
        res = super(TestMailResend, self).assertEmails(*args, **kwargs)
        self._mails.clear()

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_resend_workflow(self):
        cls = TestMailResend
        #missconfigured server
        @api.model
        def connect_failure(**kwargs):
            raise Exception
        with patch.object(IrMailServer, 'connect', side_effect=connect_failure):
            message = self.test_record.sudo().message_post(partner_ids=self.partners.ids, subtype='mail.mt_comment', message_type='notification')
        self.assertBusMessage([self.partner_admin])
        self.assertEmails(self.partner_admin, [])
        self.assertNotifStates(('exception', 'exception', 'exception', 'exception'), message)
        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        self.assertEqual(wizard.notification_ids.mapped('res_partner_id'), self.partners, "wizard should manage notifications for each failed partner")
        wizard.resend_mail_action()
        self.assertBusMessage([self.partner_admin] * 3)  # three more failure sent on bus, one for each mail in failure and one for resend
        self.assertEmails(self.partner_admin, self.partners)
        self.assertNotifStates(('exception', 'sent', 'exception', 'sent'), message)
        self.user1.write({"email": 'u1@example.com'})
        self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        self.assertBusMessage([self.partner_admin] * 2)  # two more failure update sent on bus, one for failed mail and one for resend
        self.assertEmails(self.partner_admin, self.invalid_email_partners)
        self.assertNotifStates(('sent', 'sent', 'exception', 'sent'), message)
        self.partner1.write({"email": 'p1@example.com'})
        self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        self.assertBusMessage([self.partner_admin])  # A success update should be sent on bus once the email has no more failure
        self.assertEmails(self.partner_admin, self.partner1)
        self.assertNotifStates(('sent', 'sent', 'sent', 'sent'), message)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_send_no_failure(self):
        self.user1.write({"email": 'u1@example.com'})
        self.partner1.write({"email": 'p1@example.com'})
        message = self.test_record.sudo().message_post(partner_ids=self.partners.ids, subtype='mail.mt_comment', message_type='notification')
        self.assertBusMessage([])  # one update for cancell

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_remove_mail_become_canceled(self):
        message = self.test_record.sudo().message_post(partner_ids=self.partners.ids, subtype='mail.mt_comment', message_type='notification')
        self.assertEmails(self.partner_admin, self.partners)
        self.assertBusMessage([self.partner_admin] * 2)  # two failure sent on bus, one for each mail
        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        partners = wizard.partner_ids.mapped("partner_id")
        self.assertEqual(self.invalid_email_partners, partners)
        wizard.partner_ids.filtered(lambda p: p.partner_id == self.partner1).write({"resend": False})
        wizard.resend_mail_action()
        self.assertEmails(self.partner_admin, self.user1)
        self.assertBusMessage([self.partner_admin] * 2)  # two more failure sent on bus, one for failure, one for resend
        self.assertNotifStates(('exception', 'sent', 'canceled', 'sent'), message)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_cancel_all(self):
        message = self.test_record.sudo().message_post(partner_ids=self.partners.ids, subtype='mail.mt_comment', message_type='notification')
        self.assertNotifStates(('exception', 'sent', 'exception', 'sent'), message)
        self.assertBusMessage([self.partner_admin] * 2)
        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        wizard.cancel_mail_action()
        self.assertNotifStates(('canceled', 'sent', 'canceled', 'sent'), message)
        self.assertBusMessage([self.partner_admin])  # one update for cancell
