# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    @api.model
    def default_get(self, fields):
        if self.env.context.get('default_opportunity_id'):
            self = self.with_context(
                default_res_model_id=self.env.ref('crm.model_crm_lead').id,
                default_res_id=self.env.context['default_opportunity_id']
            )
        defaults = super(CalendarEvent, self).default_get(fields)

        # sync res_model / res_id to opportunity id (aka creating meeting from lead chatter)
        if 'opportunity_id' not in defaults and defaults.get('res_id') and (defaults.get('res_model') or defaults.get('res_model_id')):
            if (defaults.get('res_model') and defaults['res_model'] == 'crm.lead') or (defaults.get('res_model_id') and self.env['ir.model'].sudo().browse(defaults['res_model_id']).model == 'crm.lead'):
                defaults['opportunity_id'] = defaults['res_id']

        return defaults

    def _compute_is_highlighted(self):
        super(CalendarEvent, self)._compute_is_highlighted()
        if self.env.context.get('active_model') == 'crm.lead':
            opportunity_id = self.env.context.get('active_id')
            for event in self:
                if event.opportunity_id.id == opportunity_id:
                    event.is_highlighted = True

    opportunity_id = fields.Many2one('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]")

    @api.model
    def create(self, vals):
        event = super(CalendarEvent, self).create(vals)

        if event.opportunity_id and not event.activity_ids:
            event.opportunity_id.log_meeting(event.name, event.start, event.duration)
        return event
