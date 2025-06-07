# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sms.tests.common import SMSCommon
from odoo.addons.test_mail_sms.tests.common import TestSMSRecipients
from odoo.tests import tagged
from odoo.tools import mute_logger


class TestSMSActionsCommon(SMSCommon, TestSMSRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestSMSActionsCommon, cls).setUpClass()
        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
        })
        cls.test_record = cls._reset_mail_context(cls.test_record)
        cls.msg = cls.test_record.message_post(body='TEST BODY', author_id=cls.partner_employee.id)
        cls.sms_p1 = cls.env['sms.sms'].create({
            'body': 'TEST BODY',
            'failure_type': 'sms_number_format',
            'mail_message_id': cls.msg.id,
            'uuid': 'e91d874e-d55f-4cf6-9d08-38ff912c6efd',
            'number': cls.partner_1.mobile,
            'partner_id': cls.partner_1.id,
            'state': 'error',
        })
        cls.notif_p1 = cls.env['mail.notification'].create({
            'author_id': cls.msg.author_id.id,
            'mail_message_id': cls.msg.id,
            'res_partner_id': cls.partner_1.id,
            'sms_id_int': cls.sms_p1.id,
            'sms_number': cls.partner_1.mobile,
            'sms_tracker_ids': [Command.create({'sms_uuid': cls.sms_p1.uuid})],
            'notification_type': 'sms',
            'notification_status': 'exception',
            'failure_type': 'sms_number_format',
        })
        cls.sms_p2 = cls.env['sms.sms'].create({
            'body': 'TEST BODY',
            'failure_type': 'sms_credit',
            'mail_message_id': cls.msg.id,
            'number': cls.partner_2.mobile,
            'partner_id': cls.partner_2.id,
            'state': 'error',
            'uuid': 'bab41209-7b14-48c1-ae21-c45ceed7e728',
        })
        cls.notif_p2 = cls.env['mail.notification'].create({
            'author_id': cls.msg.author_id.id,
            'mail_message_id': cls.msg.id,
            'res_partner_id': cls.partner_2.id,
            'sms_id_int': cls.sms_p2.id,
            'sms_number': cls.partner_2.mobile,
            'sms_tracker_ids': [Command.create({'sms_uuid': cls.sms_p2.uuid})],
            'notification_type': 'sms',
            'notification_status': 'exception',
            'failure_type': 'sms_credit',
        })


@tagged('sms_management')
class TestSMSActions(TestSMSActionsCommon):

    def test_sms_notify_cancel(self):
        self._reset_bus()

        with self.with_user('employee'):
            self.test_record.with_user(self.env.user).notify_cancel_by_type('sms')
            self.assertEqual((self.notif_p1 | self.notif_p2).mapped('notification_status'), ['canceled', 'canceled'])

        self.assertMessageBusNotifications(self.msg)

    def test_sms_set_cancel(self):
        self._reset_bus()
        self.sms_p1.action_set_canceled()
        self.assertEqual(self.sms_p1.state, 'canceled')

        self.assertMessageBusNotifications(self.msg)
        self.assertSMSNotification([
            {'partner': self.partner_1, 'number': self.notif_p1.sms_number, 'state': 'canceled', 'failure_type': 'sms_number_format'},
            {'partner': self.partner_2, 'number': self.notif_p2.sms_number, 'state': 'exception', 'failure_type': 'sms_credit'}
        ], 'TEST BODY', self.msg, check_sms=False)    # do not check new sms as they already exist

        self._reset_bus()
        self.sms_p2.with_context(sms_skip_msg_notification=True).action_set_canceled()
        self.assertEqual(self.sms_p2.state, 'canceled')

        self.assertEqual(self.env['bus.bus'].search([]), self.env['bus.bus'], 'SMS: no bus notifications unless asked')
        self.assertSMSNotification([
            {'partner': self.partner_1, 'number': self.notif_p1.sms_number, 'state': 'canceled', 'failure_type': 'sms_number_format'},
            {'partner': self.partner_2, 'number': self.notif_p2.sms_number, 'state': 'canceled', 'failure_type': 'sms_credit'}
        ], 'TEST BODY', self.msg, check_sms=False)    # do not check new sms as they already exist

    def test_sms_set_error(self):
        self._reset_bus()
        (self.sms_p1 + self.sms_p2).with_context(sms_skip_msg_notification=True).action_set_canceled()
        self.assertEqual(self.sms_p1.state, 'canceled')
        self.assertEqual(self.sms_p2.state, 'canceled')
        self.assertEqual(self.env['bus.bus'].search([]), self.env['bus.bus'], 'SMS: no bus notifications unless asked')

        (self.sms_p1 + self.sms_p2).action_set_error('sms_server')
        self.assertEqual(self.sms_p1.state, 'error')
        self.assertEqual(self.sms_p2.state, 'error')

        self.assertMessageBusNotifications(self.msg)
        self.assertSMSNotification([
            {'partner': self.partner_1, 'number': self.notif_p1.sms_number, 'state': 'exception', 'failure_type': 'sms_server'},
            {'partner': self.partner_2, 'number': self.notif_p2.sms_number, 'state': 'exception', 'failure_type': 'sms_server'}
        ], 'TEST BODY', self.msg, check_sms=False)    # do not check new sms as they already exist

    def test_sms_set_outgoing(self):
        self._reset_bus()
        (self.sms_p1 + self.sms_p2).action_set_outgoing()
        self.assertEqual(self.sms_p1.state, 'outgoing')
        self.assertEqual(self.sms_p2.state, 'outgoing')

        self.assertMessageBusNotifications(self.msg)
        self.assertSMSNotification([
            {'partner': self.partner_1, 'number': self.notif_p1.sms_number, 'state': 'ready'},
            {'partner': self.partner_2, 'number': self.notif_p2.sms_number, 'state': 'ready'}
        ], 'TEST BODY', self.msg, check_sms=False)    # do not check new sms as they already exist


@tagged('sms_management')
class TestSMSWizards(TestSMSActionsCommon):

    @mute_logger('odoo.addons.sms.models.sms_sms')
    def test_sms_resend(self):
        self._reset_bus()

        with self.with_user('employee'):
            wizard = self.env['sms.resend'].with_context(default_mail_message_id=self.msg.id).create({})
            wizard.write({'recipient_ids': [(1, r.id, {'resend': True}) for r in wizard.recipient_ids]})
            with self.mockSMSGateway():
                wizard.action_resend()

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'pending'},
            {'partner': self.partner_2, 'state': 'pending'}
        ], 'TEST BODY', self.msg, check_sms=True)
        self.assertMessageBusNotifications(self.msg, count=2)

    @mute_logger('odoo.addons.sms.models.sms_sms')
    def test_sms_resend_update_number(self):
        self._reset_bus()

        with self.with_user('employee'):
            wizard = self.env['sms.resend'].with_context(default_mail_message_id=self.msg.id).create({})
            wizard.write({'recipient_ids': [(1, r.id, {'resend': True, 'sms_number': self.random_numbers[idx]}) for idx, r in enumerate(wizard.recipient_ids.sorted())]})
            with self.mockSMSGateway():
                wizard.action_resend()

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'pending', 'number': self.random_numbers_san[0]},
            {'partner': self.partner_2, 'state': 'pending', 'number': self.random_numbers_san[1]}
        ], 'TEST BODY', self.msg, check_sms=True)
        self.assertMessageBusNotifications(self.msg, count=2)

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

    @mute_logger('odoo.addons.sms.models.sms_sms')
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

    @mute_logger('odoo.addons.sms.models.sms_sms')
    def test_sms_resend_w_cancel(self):
        self._reset_bus()

        with self.with_user('employee'):
            wizard = self.env['sms.resend'].with_context(default_mail_message_id=self.msg.id).create({})
            wizard.write({'recipient_ids': [(1, r.id, {'resend': True if r.partner_id == self.partner_1 else False}) for r in wizard.recipient_ids]})
            with self.mockSMSGateway():
                wizard.action_resend()

        self.assertSMSNotification([{'partner': self.partner_1, 'state': 'pending'}], 'TEST BODY', self.msg, check_sms=True)
        self.assertSMSNotification([{'partner': self.partner_2, 'state': 'canceled', 'number': self.notif_p2.sms_number, 'failure_type': 'sms_credit'}], 'TEST BODY', self.msg, check_sms=False)
        self.assertMessageBusNotifications(self.msg, count=2)
