# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEvent(models.Model):

    _inherit = 'calendar.event'

    opportunity_id = fields.Many2one('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]")

    @api.model
    def create(self, vals):
        event = super(CalendarEvent, self).create(vals)
        if event.opportunity_id:
            event.opportunity_id.log_meeting(event.name, event.start, event.duration)
        return event
