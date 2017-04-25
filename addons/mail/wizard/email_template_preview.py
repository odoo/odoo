# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TemplatePreview(models.TransientModel):
    _inherit = "mail.template"
    _name = "email_template.preview"
    _description = "Email Template Preview"

    @api.model
    def _get_default_record(self):
        template_id = self._context.get('template_id')
        template = self.env['mail.template'].browse(int(template_id))
        default_res_id = self._context.get('default_res_id')
        RelationalModel = self.env[template.model_id.model]
        return RelationalModel.browse(default_res_id) or RelationalModel.search([], limit=1)

    @api.model
    def default_get(self, fields):
        result = super(TemplatePreview, self).default_get(fields)

        if 'res_id' in fields and not result.get('res_id'):
            record = self._get_default_record()
            result['res_id'] = record.id
        if self._context.get('template_id') and 'model_id' in fields and not result.get('model_id'):
            result['model_id'] = self.env['mail.template'].browse(self._context['template_id']).model_id.id
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(TemplatePreview, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if 'res_id' in res['fields']:
            template_id = self._context.get('template_id')
            template = self.env['mail.template'].browse(int(template_id))
            res['fields']['res_id']['relation'] = template.model_id.model
        return res

    res_id = fields.Many2one('dummy.relational', 'Sample Document')
    partner_ids = fields.Many2many('res.partner', string='Recipients')

    @api.onchange('res_id')
    @api.multi
    def on_change_res_id(self):
        mail_values = {}
        if self.res_id and self._context.get('template_id'):
            template = self.env['mail.template'].browse(self._context['template_id'])
            self.name = template.name
            mail_values = template.generate_email(self.res_id.id)
        for field in ['email_from', 'email_to', 'email_cc', 'reply_to', 'subject', 'body_html', 'partner_to', 'partner_ids', 'attachment_ids']:
            setattr(self, field, mail_values.get(field, False))


class DummyRelation(models.AbstractModel):
    _name = "dummy.relational"
