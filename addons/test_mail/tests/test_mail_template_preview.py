# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

class TestMailTemplatePreview(TransactionCase):

    def test_generate_mail_with_context_template_preview_lang(self):
        self.env['res.lang']._activate_lang('fr_FR')
        partner = self.env['res.partner'].create([{
            'name': 'Bart',
        }])
        body_html_en = '<p>name: ${object.name}</p>'
        body_html_fr = '<p>nom: ${object.name}</p>'
        email_template = self.env['mail.template'].create({
            'name': 'TestTemplate',
            'body_html': body_html_en,
            'model_id': self.env['ir.model']._get('res.partner').id,
        })

        self.env['ir.translation'].create({
            'type': 'model',
            'name': 'mail.template,body_html',
            'lang': 'fr_FR',
            'res_id': email_template.id,
            'src': body_html_en,
            'value': body_html_fr,
        })

        preview = self.env['mail.template.preview'].create({
            'mail_template_id': email_template.id,
            'resource_ref': partner,
            'lang': 'fr_FR',
        })

        self.assertEqual(preview.body_html, '<p>nom: Bart</p>', '"name" should have been translated with "nom"')
