# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarAttendee(models.Model):
    _inherit = 'calendar.attendee'

    google_internal_event_id = fields.Char('Google Calendar Event Id')
    date_synchro = fields.Datetime('Odoo Synchro Date')

    _sql_constraints = [('google_id_uniq', 'unique(google_internal_event_id,partner_id,event_id)', 'Google ID should be unique!')]

    @api.multi
    def write(self, vals):
        for record in self:
            event_id = vals.get('event_id', record.event_id.id)

            # If attendees are updated, we need to specify that next synchro need an action
            # Except if it come from an update_from_google
            if not self.env.context.get('curr_attendee') and not self.env.context.get('NewMeeting'):
                self.env['calendar.event'].browse(event_id).write({'oe_update_date': fields.Datetime.now()})
        return super(CalendarAttendee, self).write(vals)
