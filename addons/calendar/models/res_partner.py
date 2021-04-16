# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    calendar_last_notif_ack = fields.Datetime(
        'Last notification marked as read from base Calendar', default=fields.Datetime.now)

    def get_attendee_detail(self, meeting_ids):
        """ Return a list of dict of the given meetings with the attendees details
            Used by:
                - base_calendar.js : Many2ManyAttendee
                - calendar_model.js (calendar.CalendarModel)
        """
        attendees_details = []
        meetings = self.env['calendar.event'].browse(meeting_ids)
        meetings_attendees = meetings.mapped('attendee_ids')
        for partner in self:
            partner_info = partner.name_get()[0]
            for attendee in meetings_attendees.filtered(lambda att: att.partner_id == partner):
                attendee_is_organizer = self.env.user == attendee.event_id.user_id and attendee.partner_id == self.env.user.partner_id
                attendees_details.append({
                    'id': partner_info[0],
                    'name': partner_info[1],
                    'color': partner.color,
                    'status': attendee.state,
                    'event_id': attendee.event_id.id,
                    'attendee_id': attendee.id,
                    'is_alone': attendee.event_id.is_organizer_alone and attendee_is_organizer,
                })
        return attendees_details

    @api.model
    def _set_calendar_last_notif_ack(self):
        partner = self.env['res.users'].browse(self.env.context.get('uid', self.env.uid)).partner_id
        partner.write({'calendar_last_notif_ack': datetime.now()})
