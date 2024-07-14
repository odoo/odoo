# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MarketingCampaignTest(models.TransientModel):
    _name = 'marketing.campaign.test'
    _description = 'Marketing Campaign: Launch a Test'

    @api.model
    def default_get(self, default_fields):
        defaults = super(MarketingCampaignTest, self).default_get(default_fields)
        if 'res_id' in default_fields and not defaults.get('res_id'):
            model_name = defaults.get('model_name')
            if not model_name and defaults.get('campaign_id'):
                model_name = self.env['marketing.campaign'].browse(defaults['campaign_id']).model_name
            if model_name:
                resource = self.env[model_name].search([], limit=1)
                defaults['res_id'] = resource.id
        return defaults

    @api.model
    def _selection_target_model(self):
        models = self.env['ir.model'].sudo().search([('is_mail_thread', '=', True)])
        return [(model.model, model.name) for model in models]

    campaign_id = fields.Many2one(
        'marketing.campaign', string='Campaign', required=True)
    model_id = fields.Many2one('ir.model', string='Model', related='campaign_id.model_id', readonly=True)
    model_name = fields.Char('Record model', related='campaign_id.model_id.model', readonly=True)
    res_id = fields.Integer(string='Record ID', index=True)
    resource_ref = fields.Reference(
        string='Record', selection='_selection_target_model',
        compute='_compute_resource_ref', inverse='_set_resource_ref')

    @api.depends('model_name', 'res_id')
    def _compute_resource_ref(self):
        for participant in self:
            if participant.model_name:
                participant.resource_ref = '%s,%s' % (participant.model_name, participant.res_id or 0)

    def _set_resource_ref(self):
        for participant in self:
            if participant.resource_ref:
                participant.res_id = participant.resource_ref.id

    def action_launch_test(self):
        """ Create test participant based on user choice. """
        participant = self.env['marketing.participant'].create({
            'campaign_id': self.campaign_id.id,
            'res_id': self.res_id,
            'is_test': True,
        })
        return {
            'name': _('Launch a Test'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'marketing.participant',
            'res_id': participant.id,
            'target': 'current',
        }
