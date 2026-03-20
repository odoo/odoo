# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.test_mail_template import TestMailTemplateCommon
from odoo.tests import Form, tagged, users


@tagged('mail_template', 'multi_lang')
@tagged('at_install', '-post_install')  # LEGACY at_install
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

        self.assertIn(f'<p>EnglishBody for {test_record.name}</p>', preview.body_html)
        self.assertTrue(preview.attachment_ids, 'Reports should be listed in attachments')

    def test_mail_template_preview_body(self):
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

        # Test that notification layout is applied on the preview body when the template is configured with one
        self.env.ref('mail.test_layout').arch_db = self.default_arch_db_layout
        test_template.email_layout_xmlid = 'mail.test_layout'

        preview._compute_mail_template_fields()
        # Test that header is shown in the body
        self.assertIn('HEADER', preview.body_html)
        self.assertIn("<p>EnglishBody for %s</p>" % test_record.name, preview.body_html)
        self.assertNotIn(f'Sent by {self.env.company.name}', preview.body_html)

        test_template.email_layout_force_footer = True
        preview._compute_mail_template_fields()
        self.assertIn('HEADER', preview.body_html)
        self.assertIn("<p>EnglishBody for %s</p>" % test_record.name, preview.body_html)
        self.assertIn(f'Sent by {self.env.company.name}', preview.body_html)

    @users('employee')
    def test_mail_template_preview_recipients(self):
        form = Form(self.test_template_preview.with_context(default_resource_ref=self.test_record))

        # Recipient names include partner names, email_to and email_cc
        expected_recipients_names = [
            # or to match the computation
            self.user_admin.partner_id.email_formatted or self.user_admin.partner_id.name,
            self.partner_2.email_formatted or self.partner_2.name,
            self.email_1,
            self.email_2,
            self.email_3,
        ]

        self.assertListEqual(sorted(form.recipient_names.split(', ')), sorted(expected_recipients_names))

    @users('employee')
    def test_mail_template_preview_recipients_use_default_to(self):
        self.test_template.use_default_to = True
        form = Form(self.test_template_preview.with_context(default_resource_ref=self.test_record))

        self.assertEqual(form.recipient_names, f"{self.test_record.email_from}")
