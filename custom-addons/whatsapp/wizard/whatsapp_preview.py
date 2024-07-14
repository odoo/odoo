# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WhatsAppPreview(models.TransientModel):
    _name = 'whatsapp.preview'
    _description = 'Preview template'

    wa_template_id = fields.Many2one(comodel_name="whatsapp.template", string="Templates")
    preview_whatsapp = fields.Html(compute="_compute_preview_whatsapp", string="Message Preview")

    @api.depends('wa_template_id')
    def _compute_preview_whatsapp(self):
        for record in self:
            if record.wa_template_id:
                record.preview_whatsapp = self.env['ir.qweb']._render('whatsapp.template_message_preview', {
                    'body': self.wa_template_id._get_formatted_body(demo_fallback=True),
                    'buttons': record.wa_template_id.button_ids,
                    'header_type': record.wa_template_id.header_type,
                    'footer_text': record.wa_template_id.footer_text,
                    'language_direction': 'rtl' if record.wa_template_id.lang_code in ('ar', 'he', 'fa', 'ur') else 'ltr',
                })
            else:
                record.preview_whatsapp = None
