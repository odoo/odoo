# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.common import TestMailCommon, TestRecipients
from odoo.tests import tagged, users
from odoo.tests.common import Form

@tagged('mail_template')
class TestMailTemplateTools(TestMailCommon, TestRecipients):
    @classmethod
    def setUpClass(cls):
        super(TestMailTemplateTools, cls).setUpClass()
        cls.test_record = cls.env['mail.test.simple'].with_context(cls._test_context).create({
            'email_from': 'ignasse@example.com',
            'name': 'Test',
        })

        cls.test_template = cls._create_template('mail.test.simple', {
            'body_html': '<p>EnglishBody for <t t-out="object.name"/></p>',
            'email_to': '%s, %s' % ('test1@example.com', 'test2@example.com'),
            'email_cc': '%s' % cls.partner_1.email,
            'partner_to': '%s,%s' % (cls.partner_2.id, cls.user_admin.partner_id.id),
            'subject': 'EnglishSubject for {{ object.name }}',
        })
        cls.test_template_preview = cls.env['mail.template.preview'].create({
            'mail_template_id': cls.test_template.id,
        })

    def test_initial_values(self):
        self.assertTrue(self.test_template.email_to)
        self.assertTrue(self.test_template.email_cc)
        self.assertEqual(len(self.test_template.partner_to.split(',')), 2)
        self.assertTrue(self.test_record.email_from)

    @users('employee')
    def test_mail_template_preview_recipients(self):
        form = Form(self.test_template_preview)
        form.resource_ref = self.test_record

        self.assertEqual(form.email_to, self.test_template.email_to)
        self.assertEqual(form.email_cc, self.test_template.email_cc)
        self.assertEqual(set(record.id for record in form.partner_ids),
                         {int(pid) for pid in self.test_template.partner_to.split(',') if pid})

    @users('employee')
    def test_mail_template_preview_recipients_use_default_to(self):
        self.test_template.use_default_to = True
        form = Form(self.test_template_preview)
        form.resource_ref = self.test_record

        self.assertEqual(form.email_to, self.test_record.email_from)
        self.assertFalse(form.email_cc)
        self.assertFalse(form.partner_ids)
