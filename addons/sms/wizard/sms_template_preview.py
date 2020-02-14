# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SMSTemplatePreview(models.TransientModel):
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
        sms_template_id = self.env.context.get('default_sms_template_id')
        if not sms_template_id or 'resource_ref' not in fields:
            return result
        sms_template = self.env['sms.template'].browse(sms_template_id)
        res = self.env[sms_template.model_id.model].search([], limit=1)
        if res:
            result['resource_ref'] = '%s,%s' % (sms_template.model_id.model, res.id)
        return result

    sms_template_id = fields.Many2one('sms.template') # NOTE This should probably be required

    lang = fields.Selection(_selection_languages, string='Template Preview Language')
    model_id = fields.Many2one('ir.model', related="sms_template_id.model_id")
    body = fields.Char('Body', compute='_compute_sms_template_fields')
    resource_ref = fields.Reference(string='Record reference', selection='_selection_target_model')
    no_record = fields.Boolean('No Record', compute='_compute_no_record')

    @api.depends('model_id')
    def _compute_no_record(self):
        for preview in self:
            preview.no_record = (self.env[preview.model_id.model].search_count([]) == 0) if preview.model_id else True

    @api.depends('lang', 'resource_ref')
    def _compute_sms_template_fields(self):
        for wizard in self:
            # Update body depending of the resource_ref
            sms_template = wizard.sms_template_id.with_context(lang=wizard.lang)
            wizard.body = sms_template._render_template(sms_template.body, sms_template.model, wizard.resource_ref.id) if wizard.resource_ref else sms_template.body
