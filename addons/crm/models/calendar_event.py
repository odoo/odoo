# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'
    phonecall_id = fields.Many2one('crm.phonecall', string='Phonecall')
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', domain="[('lead_type', '=', 'opportunity')]")

    @api.model
    def create(self, vals):
        calendar_event = super(CalendarEvent, self).create(vals)
        if calendar_event.opportunity_id:
            calendar_event.opportunity_id.log_meeting(calendar_event.name, calendar_event.start, calendar_event.duration)
        return calendar_event
