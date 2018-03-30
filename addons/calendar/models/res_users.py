# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, modules, _


class Users(models.Model):
    _inherit = 'res.users'

    def _systray_get_calendar_event_domain(self):
        start_dt = datetime.datetime.utcnow()
        start_date = datetime.date.today()
        end_dt = datetime.datetime.combine(start_date, datetime.time.max)

        return ['&', '|',
                '&',
                    '|', ['start', '>=', fields.Datetime.to_string(start_dt)], ['stop', '>=', fields.Datetime.to_string(start_dt)],
                    ['start', '<=', fields.Datetime.to_string(end_dt)],
                '&', ['allday', '=', True], ['start_date', '=', fields.Date.to_string(start_date)],
                '&', ('attendee_ids.partner_id', '=', self.env.user.partner_id.id), ('attendee_ids.state', '!=', 'declined')]

    @api.model
    def systray_get_activities(self):
        res = super(Users, self).systray_get_activities()

        meetings_lines = self.env['calendar.event'].search_read(
            self._systray_get_calendar_event_domain(),
            ['id', 'start', 'name', 'allday'],
            order='start')
        if meetings_lines:
            meeting_label = _("Today's Meetings")
            meetings_systray = {
                'type': 'meeting',
                'name': meeting_label,
                'model': 'calendar.event',
                'icon': modules.module.get_module_icon(self.env['calendar.event']._original_module),
                'meetings': meetings_lines,
            }
            res.insert(0, meetings_systray)

        return res
