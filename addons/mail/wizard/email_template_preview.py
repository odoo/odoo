# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TemplatePreview(models.TransientModel):
    _inherit = "mail.template"
    _name = "email_template.preview"
    _description = "Email Template Preview"

    @api.model
    def _get_records(self):
        """ Return Records of particular Email Template's Model """
        template_id = self._context.get('template_id')
        default_res_id = self._context.get('default_res_id')
        if not template_id:
            return []
        template = self.env['mail.template'].browse(int(template_id))
        records = self.env[template.model_id.model].search([], order="id desc", limit=10)
        records |= records.browse(default_res_id)
        return records.name_get()

    @api.model
    def _get_languages(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def default_get(self, fields):
        result = super(TemplatePreview, self).default_get(fields)

        template = self._context.get('template_id') and self.env['mail.template'].browse(self._context['template_id']) or False
        if 'res_id' in fields and not result.get('res_id'):
            records = self._get_records()
            result['res_id'] = records and records[0][0] or False  # select first record as a Default
        if template and 'model_id' in fields and not result.get('model_id'):
            result['model_id'] = template.model_id.id
        if template and 'preview_lang' in fields and not result.get('preview_lang') and result.get('res_id'):
            result['preview_lang'] = template.lang and template.generate_email(result['res_id'], ['lang'])['lang'] or template._context.get('lang')
        return result

    res_id = fields.Selection(_get_records, 'Sample Document')
    partner_ids = fields.Many2many('res.partner', string='Recipients')
    attachment_ids = fields.Many2many(string='Attachments', store=False)
    preview_lang = fields.Selection(_get_languages, string='Template Preview Language')

    @api.onchange('res_id', 'preview_lang')
    @api.multi
    def on_change_res_id(self):
        if not self.res_id:
            return {}
        mail_values = {}
        if self._context.get('template_id'):
            template = self.env['mail.template'].browse(self._context['template_id'])
            self.name = template.name
            mail_values = template.with_context(template_preview_lang=self.preview_lang).generate_email(self.res_id)
        for field in ['email_from', 'email_to', 'email_cc', 'reply_to', 'subject', 'body_html', 'partner_to', 'partner_ids', 'attachment_ids']:
            setattr(self, field, mail_values.get(field, False))
