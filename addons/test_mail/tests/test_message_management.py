# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import api
from odoo.addons.base.models.ir_mail_server import IrMailServer
from odoo.addons.test_mail.tests import common
from odoo.addons.test_mail.tests.common import mail_new_test_user
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_wizards')
class TestMailResend(common.BaseFunctionalTest, common.MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestMailResend, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        #Two users
        cls.user1 = mail_new_test_user(cls.env, login='e1', groups='base.group_public', name='Employee 1', email='e1')  # invalid email
        cls.user2 = mail_new_test_user(cls.env, login='e2', groups='base.group_portal', name='Employee 2', email='e2@example.com')
        #Two partner
        cls.partner1 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Partner 1',
            'email': 'p1'  # invalid email
        })
        cls.partner2 = cls.env['res.partner'].with_context(cls._test_context).create({
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

    def assertPartnerNotif(self, partner, state, message):
        # TDE CLEANME: quick fix, should be cleaned and moved to mail testing tools
        notif = self.env['mail.notification'].search([
            ('res_partner_id', '=', partner.id),
            ('mail_message_id', '=', message.id)]
        )
        self.assertEquals(notif.notification_status, state)
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
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype='mail.mt_comment', message_type='notification')
        self.assertBusMessage([self.partner_admin])
        self.assertEmails(self.partner_admin, [])
        for partner in [self.user1.partner_id, self.user2.partner_id, self.partner1, self.partner2]:
            self.assertPartnerNotif(partner, 'exception', message)

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        self.assertEqual(wizard.notification_ids.mapped('res_partner_id'), self.partners, "wizard should manage notifications for each failed partner")
        wizard.resend_mail_action()
        self.assertBusMessage([self.partner_admin] * 3)  # three more failure sent on bus, one for each mail in failure and one for resend
        self.assertEmails(self.partner_admin, self.partners)
        for partner in [self.user1.partner_id, self.partner1]:
            self.assertPartnerNotif(partner, 'exception', message)
        for partner in [self.user2.partner_id, self.partner2]:
            self.assertPartnerNotif(partner, 'sent', message)

        self.user1.write({"email": 'u1@example.com'})
        self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        self.assertBusMessage([self.partner_admin] * 2)  # two more failure update sent on bus, one for failed mail and one for resend
        self.assertEmails(self.partner_admin, self.invalid_email_partners)
        for partner in [self.partner1]:
            self.assertPartnerNotif(partner, 'exception', message)
        for partner in [self.user1.partner_id, self.user2.partner_id, self.partner2]:
            self.assertPartnerNotif(partner, 'sent', message)

        self.partner1.write({"email": 'p1@example.com'})
        self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        self.assertBusMessage([self.partner_admin])  # A success update should be sent on bus once the email has no more failure
        self.assertEmails(self.partner_admin, self.partner1)
        for partner in [self.user1.partner_id, self.user2.partner_id, self.partner1, self.partner2]:
            self.assertPartnerNotif(partner, 'sent', message)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_send_no_failure(self):
        self.user1.write({"email": 'u1@example.com'})
        self.partner1.write({"email": 'p1@example.com'})
        message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype='mail.mt_comment', message_type='notification')
        self.assertBusMessage([])  # one update for cancell

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_remove_mail_become_canceled(self):
        message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype='mail.mt_comment', message_type='notification')
        self.assertEmails(self.partner_admin, self.partners)
        self.assertBusMessage([self.partner_admin] * 2)  # two failure sent on bus, one for each mail
        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        partners = wizard.partner_ids.mapped("partner_id")
        self.assertEqual(self.invalid_email_partners, partners)
        wizard.partner_ids.filtered(lambda p: p.partner_id == self.partner1).write({"resend": False})
        wizard.resend_mail_action()
        self.assertEmails(self.partner_admin, self.user1)
        self.assertBusMessage([self.partner_admin] * 2)  # two more failure sent on bus, one for failure, one for resend
        for partner in [self.user1.partner_id]:
            self.assertPartnerNotif(partner, 'exception', message)
        for partner in [self.partner1]:
            self.assertPartnerNotif(partner, 'canceled', message)
        for partner in [self.user2.partner_id, self.partner2]:
            self.assertPartnerNotif(partner, 'sent', message)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_cancel_all(self):
        message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype='mail.mt_comment', message_type='notification')
        for partner in [self.user1.partner_id, self.partner1]:
            self.assertPartnerNotif(partner, 'exception', message)
        for partner in [self.user2.partner_id, self.partner2]:
            self.assertPartnerNotif(partner, 'sent', message)
        self.assertBusMessage([self.partner_admin] * 2)
        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        wizard.cancel_mail_action()
        for partner in [self.user1.partner_id, self.partner1]:
            self.assertPartnerNotif(partner, 'canceled', message)
        for partner in [self.user2.partner_id, self.partner2]:
            self.assertPartnerNotif(partner, 'sent', message)
        self.assertBusMessage([self.partner_admin])  # one update for cancell
