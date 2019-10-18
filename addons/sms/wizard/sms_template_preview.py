# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SMSTemplatePreview(models.TransientModel):
    _inherit = "sms.template"
    _name = "sms.template.preview"
    _description = "SMS Template Preview"

    @api.model
    def _selection_target_model(self):
        models = self.env['ir.model'].search([])
        return [(model.model, model.name) for model in models]

    @api.model
    def _selection_languages(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def default_get(self, fields):
        result = super(SMSTemplatePreview, self).default_get(fields)
        sms_template = self._context.get('default_sms_template_id') and self.env['sms.template'].browse(self._context['default_sms_template_id']) or False
        if sms_template and not result.get('res_id'):
            result['res_id'] = self.env[sms_template.model].search([], limit=1)
        return result

    sms_template_id = fields.Many2one('sms.template') # NOTE This should probably be required

    lang = fields.Selection(_selection_languages, string='Template Preview Language')
    model_id = fields.Many2one('ir.model', related="sms_template_id.model_id")
    res_id = fields.Integer(string='Record ID')
    resource_ref = fields.Reference(string='Record reference', selection='_selection_target_model', compute='_compute_resource_ref', inverse='_inverse_resource_ref')

    @api.depends('model_id', 'res_id')
    def _compute_resource_ref(self):
        for preview in self:
            if preview.model_id:
                preview.resource_ref = '%s,%s' % (preview.model_id.model, preview.res_id or 0)
            else:
                preview.resource_ref = False

    def _inverse_resource_ref(self):
        for preview in self:
            if preview.resource_ref:
                preview.res_id = preview.resource_ref.id

    @api.onchange('lang', 'resource_ref')
    def on_change_resource_ref(self):
        # Update res_id and body depending of the resource_ref
        if self.resource_ref:
            self.res_id = self.resource_ref.id
        if self.sms_template_id:
            template = self.sms_template_id.with_context(lang=self.lang)
            self.body = template._render_template(template.body, template.model, self.res_id or 0)
