# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_mail.tests.common import TestMailCommon
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('mail_wizards')
class TestMailResend(TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailResend, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({'name': 'Test', 'email_from': 'ignasse@example.com'})

        #Two users
        cls.user1 = mail_new_test_user(cls.env, login='e1', groups='base.group_public', name='Employee 1', notification_type='email', email='e1')  # invalid email
        cls.user2 = mail_new_test_user(cls.env, login='e2', groups='base.group_portal', name='Employee 2', notification_type='email', email='e2@example.com')
        #Two partner
        cls.partner1 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Partner 1',
            'email': 'p1'  # invalid email
        })
        cls.partner2 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Partner 2',
            'email': 'p2@example.com'
        })
        cls.partners = cls.env['res.partner'].concat(cls.user1.partner_id, cls.user2.partner_id, cls.partner1, cls.partner2)
        cls.invalid_email_partners = cls.env['res.partner'].concat(cls.user1.partner_id, cls.partner1)

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_resend_workflow(self):
        with self.assertSinglePostNotifications(
                [{'partner': partner, 'type': 'email', 'status': 'exception'} for partner in self.partners],
                message_info={'message_type': 'notification'},
                sim_error='connect_failure'):
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        self.assertEqual(wizard.notification_ids.mapped('res_partner_id'), self.partners, "wizard should manage notifications for each failed partner")

        # three more failure sent on bus, one for each mail in failure and one for resend
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)] * 3):
            wizard.resend_mail_action()
        done_msgs, done_notifs = self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'exception' if partner in self.user1.partner_id | self.partner1 else 'sent'} for partner in self.partners]}]
        )
        self.assertEqual(wizard.notification_ids, done_notifs)
        self.assertEqual(done_msgs, message)

        self.user1.write({"email": 'u1@example.com'})

        # two more failure update sent on bus, one for failed mail and one for resend
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)] * 2):
            self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        done_msgs, done_notifs = self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'exception' if partner == self.partner1 else 'sent', 'check_send': partner == self.partner1} for partner in self.partners]}]
        )
        self.assertEqual(wizard.notification_ids, done_notifs)
        self.assertEqual(done_msgs, message)

        self.partner1.write({"email": 'p1@example.com'})

        # A success update should be sent on bus once the email has no more failure
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)]):
            self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({}).resend_mail_action()
        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'sent', 'check_send': partner == self.partner1} for partner in self.partners]}]
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_remove_mail_become_canceled(self):
        # two failure sent on bus, one for each mail
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)] * 2):
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email', 'status': 'exception' if partner in self.user1.partner_id | self.partner1 else 'sent'} for partner in self.partners]}]
        )

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        partners = wizard.partner_ids.mapped("partner_id")
        self.assertEqual(self.invalid_email_partners, partners)
        wizard.partner_ids.filtered(lambda p: p.partner_id == self.partner1).write({"resend": False})
        wizard.resend_mail_action()

        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email',
                        'status': (partner == self.user1.partner_id and 'exception') or (partner == self.partner1 and 'canceled') or 'sent'} for partner in self.partners]}]
        )

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_cancel_all(self):
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)] * 2):
            message = self.test_record.with_user(self.user_admin).message_post(partner_ids=self.partners.ids, subtype_xmlid='mail.mt_comment', message_type='notification')

        wizard = self.env['mail.resend.message'].with_context({'mail_message_to_resend': message.id}).create({})
        # one update for cancell
        self._reset_bus()
        with self.mock_mail_gateway(), self.assertBus([(self.cr.dbname, 'res.partner', self.partner_admin.id)] * 1):
            wizard.cancel_mail_action()

        self.assertMailNotifications(message, [
            {'content': '', 'message_type': 'notification',
             'notif': [{'partner': partner, 'type': 'email',
                        'check_send': partner in self.user1.partner_id | self.partner1,
                        'status': 'canceled' if partner in self.user1.partner_id | self.partner1 else 'sent'} for partner in self.partners]}]
        )
