# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, modules, _
from pytz import timezone, UTC


class Users(models.Model):
    _inherit = 'res.users'

    def _systray_get_calendar_event_domain(self):
        tz = self.env.user.tz
        start_dt = datetime.datetime.utcnow()
        if tz:
            start_date = timezone(tz).localize(start_dt).astimezone(UTC).date()
        else:
            start_date = datetime.date.today()
        end_dt = datetime.datetime.combine(start_date, datetime.time.max)
        if tz:
            end_dt = timezone(tz).localize(end_dt).astimezone(UTC)

        return ['&', '|',
                '&',
                    '|',
                        ['start', '>=', fields.Datetime.to_string(start_dt)],
                        ['stop', '>=', fields.Datetime.to_string(start_dt)],
                    ['start', '<=', fields.Datetime.to_string(end_dt)],
                '&',
                    ['allday', '=', True],
                    ['start_date', '=', fields.Date.to_string(start_date)],
                ('attendee_ids.partner_id', '=', self.env.user.partner_id.id)]

    @api.model
    def systray_get_activities(self):
        res = super(Users, self).systray_get_activities()

        meetings_lines = self.env['calendar.event'].search_read(
            self._systray_get_calendar_event_domain(),
            ['id', 'start', 'name', 'allday', 'attendee_status'],
            order='start')
        meetings_lines = [line for line in meetings_lines if line['attendee_status'] != 'declined']
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
