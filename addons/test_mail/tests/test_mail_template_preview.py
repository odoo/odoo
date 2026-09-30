# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.test_mail_template import TestMailTemplateCommon
from odoo.tests import Form, tagged, users


@tagged('mail_template', 'multi_lang')
class TestMailTemplateTools(TestMailTemplateCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_template_preview = cls.env['mail.template.preview'].create({
            'mail_template_id': cls.test_template.id,
        })

    def test_initial_values(self):
        self.assertTrue(self.test_template.email_to)
        self.assertTrue(self.test_template.email_cc)
        self.assertEqual(len(self.test_template.partner_to.split(',')), 2)
        self.assertTrue(self.test_record.email_from)

    @users('employee')
    def test_mail_template_preview_fields(self):
        test_record = self.test_record.with_user(self.env.user)
        test_record_ref = f'{test_record._name},{test_record.id}'
        test_template = self.test_template.with_user(self.env.user)

        # resource_ref: should not crash if no template (hence no model)
        preview = Form(self.env['mail.template.preview'])
        self.assertFalse(preview.has_attachments)
        self.assertTrue(preview.has_several_languages_installed)
        self.assertFalse(preview.resource_ref)

        # mail_template_id being invisible, create a new one for template check
        preview = Form(self.env['mail.template.preview'].with_context(default_mail_template_id=test_template.id))
        self.assertTrue(preview.has_attachments)
        self.assertTrue(preview.has_several_languages_installed)
        self.assertEqual(preview.resource_ref, test_record_ref, 'Should take first (only) record by default')

    def test_mail_template_preview_empty_database(self):
        """Check behaviour of the wizard when there is no record for the target model."""
        self.env['mail.test.lang'].search([]).unlink()
        test_template = self.env['mail.template'].browse(self.test_template.ids)
        preview = self.env['mail.template.preview'].create({
            'mail_template_id': test_template.id,
        })

        self.assertFalse(preview.error_msg)
        for field in preview._MAIL_TEMPLATE_FIELDS:
            if field in ['partner_to', 'report_template_ids']:
                continue
            self.assertEqual(test_template[field], preview[field])

    def test_mail_template_preview_dynamic_attachment(self):
        """Check behaviour with templates that use reports."""
        test_record = self.env['mail.test.lang'].browse(self.test_record.ids)
        test_report = self.env['ir.actions.report'].sudo().create({
                'name': 'Test Report',
                'model': test_record._name,
                'print_report_name': "'TestReport for %s' % object.name",
                'report_type': 'qweb-pdf',
                'report_name': 'test_mail.mail_test_ticket_test_template',
        })
        self.test_template.write({
            'report_template_ids': test_report.ids,
            'attachment_ids': False,
        })

        preview = self.env['mail.template.preview'].with_context({
            'force_report_rendering': False, # this also invalidates the test records...
            }).create({
            'mail_template_id': self.test_template.id,
            'resource_ref': test_record,
        })

        self.assertEqual(preview.body_html, f'<p>EnglishBody for {test_record.name}</p>')
        self.assertFalse(preview.attachment_ids, 'Reports should not be listed in attachments')

    def test_mail_template_preview_force_lang(self):
        test_record = self.env['mail.test.lang'].browse(self.test_record.ids)
        test_record.write({
            'lang': 'es_ES',
        })
        test_template = self.env['mail.template'].browse(self.test_template.ids)

        preview = self.env['mail.template.preview'].create({
            'mail_template_id': test_template.id,
            'resource_ref': test_record,
            'lang': 'es_ES',
        })
        self.assertEqual(preview.body_html, '<p>SpanishBody for %s</p>' % test_record.name)

        preview.write({'lang': 'en_US'})
        self.assertEqual(preview.body_html, '<p>EnglishBody for %s</p>' % test_record.name)

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
