# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail.tests import common as test_mail_common
from odoo.addons.test_mail_full.tests import common as test_mail_full_common


class TestSmsTemplate(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS, test_mail_common.MockEmails, test_mail_common.TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestSmsTemplate, cls).setUpClass()
        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
        })
        cls.test_record = cls._reset_mail_context(cls.test_record)

        cls.sms_template = cls.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': cls.env['ir.model']._get('mail.test.sms').id,
            'body': 'Dear ${object.display_name} this is an SMS.'
        })

    def test_sms_template_render(self):
        rendered_body = self.sms_template._render_template(self.sms_template.body, self.sms_template.model, self.test_record.ids)
        self.assertEqual(rendered_body[self.test_record.id], 'Dear %s this is an SMS.' % self.test_record.display_name)
