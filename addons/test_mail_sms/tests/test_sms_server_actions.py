# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sms.tests.common import SMSCommon
from odoo.addons.test_mail_sms.tests.common import TestSMSRecipients
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('ir_actions')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestServerAction(SMSCommon, TestSMSRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestServerAction, cls).setUpClass()
        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
        })
        cls.test_record_2 = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test Record 2',
            'customer_id': False,
            'phone_nbr': cls.test_numbers[0],
        })

        cls.sms_template = cls._create_sms_template('mail.test.sms')
        cls.action = cls.env['ir.actions.server'].create({
            'name': 'Test SMS Action',
            'model_id': cls.env['ir.model']._get('mail.test.sms').id,
            'state': 'sms',
            'sms_template_id': cls.sms_template.id,
            'group_ids': cls.env.ref('base.group_user'),
        })

    def test_action_sms(self):
        context = {
            'active_model': 'mail.test.sms',
            'active_ids': (self.test_record | self.test_record_2).ids,
        }

        with self.with_user('employee'), self.mockSMSGateway():
            self.action.with_user(self.env.user).with_context(**context).run()

        self.assertSMSNotification(
            [{'partner': self.test_record.customer_id, 'state': 'pending'}],
            'Dear %s this is an SMS.' % self.test_record.display_name,
            messages=self.test_record.message_ids[-1]
        )
        self.assertSMSNotification(
            [{'partner': self.env['res.partner'],
              'number': self.test_numbers_san[0],
              'state': 'pending'}],
            'Dear %s this is an SMS.' % self.test_record_2.display_name,
            messages=self.test_record_2.message_ids[-1]
        )

    def test_action_sms_single(self):
        context = {
            'active_model': 'mail.test.sms',
            'active_id': self.test_record.id,
        }

        with self.with_user('employee'), self.mockSMSGateway():
            self.action.with_user(self.env.user).with_context(**context).run()

        self.assertSMSNotification(
            [{'partner': self.test_record.customer_id, 'state': 'pending'}],
            'Dear %s this is an SMS.' % self.test_record.display_name,
            messages=self.test_record.message_ids[-1]
        )
