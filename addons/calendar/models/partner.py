# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.calendar.models.calendar import get_real_ids


class Partner(models.Model):
    _inherit = 'res.partner'

    calendar_last_notif_ack = fields.Datetime(string='Last notification marked as read from base Calendar')

    @api.multi
    def get_attendee_detail(self, meeting_id):
        """
        Return a list of tuple (id, name, status)
        Used by web_calendar.js : Many2ManyAttendee
        """
        datas = []
        meeting = meeting_id and self.env['calendar.event'].browse(get_real_ids(meeting_id)) or None
        for partner in self:
            data = [partner.id, partner.display_name, False, partner.color]
            if meeting:
                for attendee in meeting.attendee_ids.filtered(lambda attendee: attendee.partner_id == partner):
                    data[2] = attendee.state
            datas.append(data)
        return datas

    @api.model
    def _set_calendar_last_notif_ack(self):
        self.env['res.users'].browse(self._uid).partner_id.write({
            'calendar_last_notif_ack': fields.Datetime.now()
        })
        return
