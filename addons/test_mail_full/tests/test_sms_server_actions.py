# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail.tests import common as test_mail_common
from odoo.addons.test_mail_full.tests import common as test_mail_full_common


class TestSmsTemplate(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS, test_mail_common.TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestSmsTemplate, cls).setUpClass()
        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
        })
        cls.test_record_2 = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test Record 2',
            'customer_id': False,
            'phone_nbr': cls.test_numbers[0],
        })

        model_id = cls.env['ir.model']._get('mail.test.sms').id
        cls.sms_template = cls.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': model_id,
            'body': 'Dear ${object.display_name} this is an SMS.'
        })

        cls.action = cls.env['ir.actions.server'].create({
            'name': 'Test SMS Action',
            'model_id': model_id,
            'state': 'sms',
            'sms_template_id': cls.sms_template.id,
        })

    def test_action_sms(self):
        context = {
            'active_model': 'mail.test.sms',
            'active_ids': (self.test_record | self.test_record_2).ids,
        }

        with self.sudo('employee'), self.mockSMSGateway():
            self.action.with_user(self.env.user).with_context(**context).run()

        self.assertSMSOutgoing(self.test_record.customer_id, None, 'Dear %s this is an SMS.' % self.test_record.display_name)
        self.assertSMSOutgoing(self.env['res.partner'], self.test_numbers_san[0], 'Dear %s this is an SMS.' % self.test_record_2.display_name)

    def test_action_sms_single(self):
        context = {
            'active_model': 'mail.test.sms',
            'active_id': self.test_record.id,
        }

        with self.sudo('employee'), self.mockSMSGateway():
            self.action.with_user(self.env.user).with_context(**context).run()
        self.assertSMSOutgoing(self.test_record.customer_id, None, 'Dear %s this is an SMS.' % self.test_record.display_name)

    def test_action_sms_w_log(self):
        self.action.sms_mass_keep_log = True
        context = {
            'active_model': 'mail.test.sms',
            'active_ids': (self.test_record | self.test_record_2).ids,
        }

        with self.sudo('employee'), self.mockSMSGateway():
            self.action.with_user(self.env.user).with_context(**context).run()

        self.assertSMSNotification([{'partner': self.test_record.customer_id, 'state': 'ready'}], 'Dear %s this is an SMS.' % self.test_record.display_name)
        self.assertSMSNotification([{'partner': self.env['res.partner'], 'number': self.test_numbers_san[0], 'state': 'ready'}], 'Dear %s this is an SMS.' % self.test_record_2.display_name)
