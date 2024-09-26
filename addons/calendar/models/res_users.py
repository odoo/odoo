# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, modules, _
from pytz import timezone, UTC


class Users(models.Model):
    _inherit = 'res.users'

    calendar_default_privacy = fields.Selection(related='res_users_settings_id.calendar_default_privacy', readonly=False, required=True)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['calendar_default_privacy']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['calendar_default_privacy']

    def get_selected_calendars_partner_ids(self, include_user=True):
        """
        Retrieves the partner IDs of the attendees selected in the calendar view.

        :param bool include_user: Determines whether to include the current user's partner ID in the results.
        :return: A list of integer IDs representing the partners selected in the calendar view.
                 If 'include_user' is True, the list will also include the current user's partner ID.
        :rtype: list
        """
        self.ensure_one()
        partner_ids = self.env['calendar.filters'].search([
            ('user_id', '=', self.id),
            ('partner_checked', '=', True)
        ]).partner_id.ids

        if include_user:
            partner_ids += [self.env.user.partner_id.id]
        return partner_ids

    def _systray_get_calendar_event_domain(self):
        # Determine the domain for which the users should be notified. This method sends notification to
        # events occurring between now and the end of the day. Note that "now" needs to be computed in the
        # user TZ and converted into UTC to compare with the records values and "the end of the day" needs
        # also conversion. Otherwise TZ diverting a lot from UTC would send notification for events occurring
        # tomorrow.
        # The user is notified if the start is occurring between now and the end of the day
        # if the event is not finished.
        #   |           |
        #   |===========|===> DAY A (`start_dt`): now in the user TZ
        #   |           |
        #   |           | <--- `start_dt_utc`: now is on the right if the user lives
        #   |           |               in West Longitude (America for example)
        #   |           |
        #   |  -------  | <--- `start`: the start of the event (in UTC)
        #   | | event | |
        #   |  -------  | <--- `stop`: the stop of the event (in UTC)
        #   |           |
        #   |           |
        #   |           | <--- `stop_dt_utc` = `stop_dt` if user lives in an area of East longitude (positive shift compared to UTC, Belgium for example)
        #   |           |
        #   |           |
        #   |-----------| <--- `stop_dt` = end of the day for DAY A from user point of view (23:59 in this TZ)
        #   |===========|===> DAY B
        #   |           |
        #   |           | <--- `stop_dt_utc` = `stop_dt` if user lives in an area of West longitude (positive shift compared to UTC, America for example)
        #   |           |
        start_dt_utc = start_dt = datetime.datetime.now(UTC)
        stop_dt_utc = UTC.localize(datetime.datetime.combine(start_dt_utc.date(), datetime.time.max))

        tz = self.env.user.tz
        if tz:
            user_tz = timezone(tz)
            start_dt = start_dt_utc.astimezone(user_tz)
            stop_dt = user_tz.localize(datetime.datetime.combine(start_dt.date(), datetime.time.max))
            stop_dt_utc = stop_dt.astimezone(UTC)

        start_date = start_dt.date()

        current_user_non_declined_attendee_ids = self.env['calendar.attendee']._search([
            ('partner_id', '=', self.env.user.partner_id.id),
            ('state', '!=', 'declined'),
        ])

        return ['&', '|',
                '&',
                    '|',
                        ['start', '>=', fields.Datetime.to_string(start_dt_utc)],
                        ['stop', '>=', fields.Datetime.to_string(start_dt_utc)],
                    ['start', '<=', fields.Datetime.to_string(stop_dt_utc)],
                '&',
                    ['allday', '=', True],
                    ['start_date', '=', fields.Date.to_string(start_date)],
                ('attendee_ids', 'in', current_user_non_declined_attendee_ids)]

    @api.model
    def _get_activity_groups(self):
        res = super()._get_activity_groups()
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

    def check_synchronization_status(self):
        return {}
