# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from zoneinfo import ZoneInfo

from odoo import api, Command, fields, models, modules, _
from odoo.fields import Domain


class ResUsers(models.Model):
    _inherit = 'res.users'

    calendar_users = fields.One2many('calendar.calendar.user', 'user_id')
    calendar_ids = fields.Many2many('calendar.calendar', compute='_compute_calendar_ids')
    writable_calendar_ids = fields.Many2many('calendar.calendar', compute='_compute_writeable_calendar_ids')
    primary_calendar = fields.Many2one('calendar.calendar', compute='_compute_primary_calendar', store=True)

    @api.depends('calendar_ids')
    def _compute_primary_calendar(self):
        for user in self:
            user.primary_calendar = user.calendar_users.filtered(
                lambda l: l.is_primary and l.access_role == 'owner').calendar_id

    @api.depends('calendar_users')
    def _compute_calendar_ids(self):
        for user in self:
            user.sudo().calendar_ids = user.calendar_users.mapped('calendar_id')

    @api.depends('calendar_users')
    def _compute_writeable_calendar_ids(self):
        for user in self:
            user.writable_calendar_ids = (user.calendar_users.filtered(lambda l: l.access_role in ('owner', 'writer')).mapped('calendar_id'))

    def get_secondary_calendars(self):
        return self.calendar_users.filtered(lambda l: not (l.is_primary and l.access_role == 'owner')).mapped('calendar_id')

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

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        default_privacy = self.env['ir.config_parameter'].sudo().get_str('calendar.default_privacy', 'public')
        calendar_vals_list = [
            {
                'name': 'Primary Calendar',
                'calendar_default_privacy': default_privacy,
                'calendar_users': [
                    Command.create({
                        'user_id': user.id,
                        'access_role': 'owner',
                        'is_primary': True,
                        'is_filter_active': True,
                        'is_filter_checked': True,
                    }),
                ],
            }
            for user in users
        ]
        self.env['calendar.calendar'].create(calendar_vals_list)
        return users

    def _systray_get_calendar_event_domain(self):
        # Determine the domain for which the users should be notified. This method sends notification to
        # events for which there's a reminder set and occurring between now and the end of the day.
        # Note that "now" needs to be computed in the user TZ and converted into UTC to compare with the records values
        # and "the end of the day" needs also conversion. Otherwise TZ diverting a lot from UTC would send notification
        # for events occurring tomorrow.
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
        start_dt_utc = start_dt = datetime.datetime.now(datetime.UTC)
        stop_dt_utc = datetime.datetime.combine(start_dt_utc.date(), datetime.time.max.replace(tzinfo=datetime.UTC))

        tz = self.env.user.tz
        if tz:
            user_tz = ZoneInfo(tz)
            start_dt = start_dt_utc.astimezone(user_tz)
            stop_dt = datetime.datetime.combine(start_dt.date(), datetime.time.max.replace(tzinfo=user_tz, fold=1))
            stop_dt_utc = stop_dt.astimezone(datetime.UTC)

        start_date = start_dt.date()

        current_user_non_declined_attendee_ids = self.env['calendar.attendee']._search([
            ('partner_id', '=', self.env.user.partner_id.id),
            ('state', '!=', 'declined'),
        ])

        is_today_allday = Domain.AND([
            Domain('allday', '=', True),
            Domain('start_date', '=', fields.Date.to_string(start_date)),
        ])
        is_today_ongoing_or_future = Domain.AND([
            Domain.OR([
                Domain('start', '>=', fields.Datetime.to_string(start_dt_utc)),
                Domain('stop', '>=', fields.Datetime.to_string(start_dt_utc)),
            ]),
            Domain('start', '<=', fields.Datetime.to_string(stop_dt_utc)),
        ])

        return Domain.AND([
            Domain('alarm_ids', "!=", False),
            Domain('attendee_ids', 'in', current_user_non_declined_attendee_ids),
            Domain.OR([
                is_today_allday,
                is_today_ongoing_or_future,
            ])
        ])

    @api.model
    def _get_activity_groups(self):
        res = super()._get_activity_groups()
        EventModel = self.env['calendar.event']
        meetings_lines = EventModel.search_read(
            self._systray_get_calendar_event_domain(),
            ['id', 'start', 'name', 'allday'],
            order='start',
            limit=2,
        )
        if meetings_lines:
            meeting_label = _("Upcoming Meetings")
            meetings_systray = {
                'id': self.env['ir.model']._get('calendar.event').id,
                'type': 'meeting',
                'name': meeting_label,
                'is_today_meetings': True,
                'model': 'calendar.event',
                'icon': modules.module.get_module_icon(EventModel._original_module),
                'domain': [('active', 'in', [True, False])],
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

    @api.model
    def get_calendar_sync_email(self):
        """Meant to be overridden by a specific calendar provider"""
        return False

    @api.model
    def get_calendar_model_data(self):
        return {
            'credential_status': self.env.user.check_calendar_credentials(),
            'sync_status': self.env.user.check_synchronization_status(),
            'sync_email': self.env.user.get_calendar_sync_email(),
            'default_duration': self.env['calendar.event'].get_default_duration(),
        }

    def _has_any_active_synchronization(self):
        """
        Overridable method for checking if user has any synchronization active in inherited modules.

        :return: boolean indicating if any synchronization is active.
        """
        return False
