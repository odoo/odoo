# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail.tests import common as test_mail_common
from odoo.addons.test_mail_full.tests import common as test_mail_full_common


class TestSMSPost(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS, test_mail_common.MockEmails, test_mail_common.TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestSMSPost, cls).setUpClass()
        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
        })
        cls.test_record = cls._reset_mail_context(cls.test_record)

    def test_message_post_with_sms_on_partners(self):
        test_body = 'Void body'
        with self.mockSMSGateway():
            (self.partner_1 | self.partner_2).message_post_send_sms(test_body)
        self.assertSMSSent((self.partner_1 | self.partner_2).mapped('mobile'), test_body)

    def test_message_post_with_sms_w_default(self):
        test_body = 'Void body'
        with self.mockSMSGateway():
            self.test_record.message_post_send_sms(test_body)
        self.assertSMSSent(self.partner_1.mapped('mobile'), test_body)
        self.assertIn(test_body, self.test_record.message_ids.body)

    def test_message_post_with_sms_w_numbers(self):
        test_body = 'Void body'
        test_numbers = ['0475114477', '0475225588']
        with self.mockSMSGateway():
            self.test_record.message_post_send_sms(test_body, numbers=test_numbers)
        self.assertSMSSent(test_numbers, test_body)
        self.assertIn(test_body, self.test_record.message_ids.body)

    def test_message_post_with_sms_w_numbers_duplicate(self):
        test_body = 'Void body'
        test_numbers = ['0475114477', '0475225588', '0475114477']
        with self.mockSMSGateway():
            self.test_record.message_post_send_sms(test_body, numbers=test_numbers)
        self.assertSMSSent(test_numbers, test_body)
        self.assertIn(test_body, self.test_record.message_ids.body)

    def test_message_post_with_sms_w_partners(self):
        test_body = 'Void body'
        with self.mockSMSGateway():
            self.test_record.message_post_send_sms(test_body, partners=self.partner_1 | self.partner_2)
        self.assertSMSSent((self.partner_1 | self.partner_2).mapped('mobile'), test_body)
        self.assertIn(test_body, self.test_record.message_ids.body)
