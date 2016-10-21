# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEvent(models.Model):

    _inherit = 'calendar.event'

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
        if event.opportunity_id:
            event.opportunity_id.log_meeting(event.name, event.start, event.duration)
        return event
