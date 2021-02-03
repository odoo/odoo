# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models

from odoo.addons.calendar.models.calendar import get_real_ids


class Partner(models.Model):
    _inherit = 'res.partner'

    calendar_last_notif_ack = fields.Datetime('Last notification marked as read from base Calendar', default=fields.Datetime.now)

    @api.multi
    def get_attendee_detail(self, meeting_id):
        """ Return a list of tuple (id, name, status)
            Used by base_calendar.js : Many2ManyAttendee
        """
        datas = []
        meeting = None
        if meeting_id:
            meeting = self.env['calendar.event'].browse(get_real_ids(meeting_id))

        for partner in self:
            data = partner.name_get()[0]
            data = [data[0], data[1], False, partner.color]
            if meeting:
                for attendee in meeting.attendee_ids:
                    if attendee.partner_id.id == partner.id:
                        data[2] = attendee.state
            datas.append(data)
        return datas

    @api.model
    def _set_calendar_last_notif_ack(self):
        partner = self.env['res.users'].browse(self.env.context.get('uid',self.env.uid)).partner_id
        partner.write({'calendar_last_notif_ack': datetime.now()})
        return
