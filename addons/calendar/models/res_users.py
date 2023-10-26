# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, modules, _
from pytz import timezone, UTC


class Users(models.Model):
    _inherit = 'res.users'

    def _systray_get_calendar_event_domain(self):
        current_user_non_declined_attendee_ids = self.env['calendar.attendee']._search([
            ('partner_id', '=', self.env.user.partner_id.id),
            ('state', '!=', 'declined'),
        ])
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
                ('attendee_ids', 'in', current_user_non_declined_attendee_ids)]

    @api.model
    def systray_get_activities(self):
        res = super(Users, self).systray_get_activities()

        EventModel = self.env['calendar.event']
        meetings_lines = EventModel.search_read(
            self._systray_get_calendar_event_domain(),
            ['id', 'start', 'name', 'allday'],
            order='start')
        if meetings_lines:
            meeting_label = _("Today's Meetings")
            meetings_systray = {
                'id': self.env['ir.model']._get('calendar.event').id,
                'type': 'meeting',
                'name': meeting_label,
                'model': 'calendar.event',
                'icon': modules.module.get_module_icon(EventModel._original_module),
                'meetings': meetings_lines,
                "view_type": EventModel._systray_view,
            }
            res.insert(0, meetings_systray)

        return res

    @api.model
    def check_calendar_credentials(self):
        return {}
