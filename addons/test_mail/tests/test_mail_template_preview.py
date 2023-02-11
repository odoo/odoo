# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests.test_mail_template import TestMailTemplate
from odoo.tests import tagged


@tagged('mail_template')
class TestMailTemplateTools(TestMailTemplate):

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
        self.assertEqual(preview.body_html, '<p>Spanish Body for %s</p>' % test_record.name)

        preview.write({'lang': 'en_US'})
        self.assertEqual(preview.body_html, '<p>English Body for %s</p>' % test_record.name)
