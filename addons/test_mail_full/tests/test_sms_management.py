# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail_full.tests.common import TestMailFullCommon, TestRecipients


class TestSMSWizards(TestMailFullCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestSMSWizards, cls).setUpClass()
        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
        })
        cls.test_record = cls._reset_mail_context(cls.test_record)
        cls.msg = cls.test_record.message_post(body='TEST BODY', author_id=cls.partner_employee.id)
        cls.notif_p1 = cls.env['mail.notification'].create({
            'mail_message_id': cls.msg.id,
            'res_partner_id': cls.partner_1.id,
            'sms_number': cls.partner_1.mobile,
            'notification_type': 'sms',
            'notification_status': 'exception',
            'failure_type': 'sms_number_format',
        })
        cls.notif_p2 = cls.env['mail.notification'].create({
            'mail_message_id': cls.msg.id,
            'res_partner_id': cls.partner_2.id,
            'sms_number': cls.partner_2.mobile,
            'notification_type': 'sms',
            'notification_status': 'exception',
            'failure_type': 'sms_credit',
        })

    def test_sms_resend(self):
        self._reset_bus()

        with self.with_user('employee'):
            wizard = self.env['sms.resend'].with_context(default_mail_message_id=self.msg.id).create({})
            wizard.write({'recipient_ids': [(1, r.id, {'resend': True}) for r in wizard.recipient_ids]})
            with self.mockSMSGateway():
                wizard.action_resend()

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'sent'},
            {'partner': self.partner_2, 'state': 'sent'}
        ], 'TEST BODY', self.msg, check_sms=True)
        self.assertMessageBusNotifications(self.msg)

    def test_sms_resend_update_number(self):
        self._reset_bus()

        with self.with_user('employee'):
            wizard = self.env['sms.resend'].with_context(default_mail_message_id=self.msg.id).create({})
            wizard.write({'recipient_ids': [(1, r.id, {'resend': True, 'sms_number': self.random_numbers[idx]}) for idx, r in enumerate(wizard.recipient_ids.sorted())]})
            with self.mockSMSGateway():
                wizard.action_resend()

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'sent', 'number': self.random_numbers_san[0]},
            {'partner': self.partner_2, 'state': 'sent', 'number': self.random_numbers_san[1]}
        ], 'TEST BODY', self.msg, check_sms=True)
        self.assertMessageBusNotifications(self.msg)

    def test_sms_resend_cancel(self):
        self._reset_bus()

        with self.with_user('employee'):
            wizard = self.env['sms.resend'].with_context(default_mail_message_id=self.msg.id).create({})
            with self.mockSMSGateway():
                wizard.action_cancel()

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'canceled', 'number': self.notif_p1.sms_number, 'failure_type': 'sms_number_format'},
            {'partner': self.partner_2, 'state': 'canceled', 'number': self.notif_p2.sms_number, 'failure_type': 'sms_credit'}
        ], 'TEST BODY', self.msg, check_sms=False)
        self.assertMessageBusNotifications(self.msg)

    def test_sms_resend_internals(self):
        self._reset_bus()
        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'exception', 'number': self.notif_p1.sms_number, 'failure_type': 'sms_number_format'},
            {'partner': self.partner_2, 'state': 'exception', 'number': self.notif_p2.sms_number, 'failure_type': 'sms_credit'}
        ], 'TEST BODY', self.msg, check_sms=False)

        with self.with_user('employee'):
            wizard = self.env['sms.resend'].with_context(default_mail_message_id=self.msg.id).create({})
            self.assertTrue(wizard.has_insufficient_credit)
            self.assertEqual(set(wizard.mapped('recipient_ids.partner_name')), set((self.partner_1 | self.partner_2).mapped('display_name')))
            wizard.write({'recipient_ids': [(1, r.id, {'resend': True}) for r in wizard.recipient_ids]})
            with self.mockSMSGateway():
                wizard.action_resend()

    def test_sms_resend_w_cancel(self):
        self._reset_bus()

        with self.with_user('employee'):
            wizard = self.env['sms.resend'].with_context(default_mail_message_id=self.msg.id).create({})
            wizard.write({'recipient_ids': [(1, r.id, {'resend': True if r.partner_id == self.partner_1 else False}) for r in wizard.recipient_ids]})
            with self.mockSMSGateway():
                wizard.action_resend()

        self.assertSMSNotification([{'partner': self.partner_1, 'state': 'sent'}], 'TEST BODY', self.msg, check_sms=True)
        self.assertSMSNotification([{'partner': self.partner_2, 'state': 'canceled', 'number': self.notif_p2.sms_number, 'failure_type': 'sms_credit'}], 'TEST BODY', self.msg, check_sms=False)
        self.assertMessageBusNotifications(self.msg)

    def test_sms_cancel(self):
        self._reset_bus()

        with self.mockSMSGateway(), self.with_user('employee'):
            wizard = self.env['sms.cancel'].with_context(default_model=self.msg.model).create({})
            wizard.action_cancel()

            self.assertEqual((self.notif_p1 | self.notif_p2).mapped('notification_status'), ['canceled', 'canceled'])

        self.assertMessageBusNotifications(self.msg)
