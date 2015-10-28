# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from ..models.calendar import get_real_ids


class ResPartner(models.Model):
    _inherit = 'res.partner'

    calendar_last_notif_ack = fields.Datetime('Last notification marked as read from base Calendar')

    @api.multi
    def get_attendee_detail(self, meeting_id):
        """
        Return a list of tuple (id, name, status)
        Used by web_calendar.js : Many2ManyAttendee
        """
        datas = []
        meeting = None
        if meeting_id:
            meeting = self.env['calendar.event'].browse(get_real_ids(meeting_id))
        for partner in self:
            data = (partner.id, partner.name)
            data = [data[0], data[1], False, partner.color]
            if meeting:
                for attendee in meeting.attendee_ids:
                    if attendee.partner_id.id == partner.id:
                        data[2] = attendee.state
            datas.append(data)
        return datas

    @api.multi
    def _set_calendar_last_notif_ack(self):
        self.env.user.partner_id.write({'calendar_last_notif_ack': fields.Datetime.now()})
