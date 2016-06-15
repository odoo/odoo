# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from openerp.osv import osv, fields

from odoo.addons.calendar.models.calendar import get_real_ids


class res_partner(osv.Model):
    _inherit = 'res.partner'
    _columns = {
        'calendar_last_notif_ack': fields.datetime('Last notification marked as read from base Calendar'),
    }

    def get_attendee_detail(self, cr, uid, ids, meeting_id, context=None):
        """
        Return a list of tuple (id, name, status)
        Used by web_calendar.js : Many2ManyAttendee
        """
        datas = []
        meeting = None
        if meeting_id:
            meeting = self.pool['calendar.event'].browse(cr, uid, get_real_ids(meeting_id), context=context)
        for partner in self.browse(cr, uid, ids, context=context):
            data = self.name_get(cr, uid, [partner.id], context)[0]
            data = [data[0], data[1], False, partner.color]
            if meeting:
                for attendee in meeting.attendee_ids:
                    if attendee.partner_id.id == partner.id:
                        data[2] = attendee.state
            datas.append(data)
        return datas

    def _set_calendar_last_notif_ack(self, cr, uid, context=None):
        partner = self.pool['res.users'].browse(cr, uid, uid, context=context).partner_id
        self.write(cr, uid, partner.id, {'calendar_last_notif_ack': datetime.now()}, context=context)
        return
