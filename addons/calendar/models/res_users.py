# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models, modules, _
from odoo.exceptions import AccessError

from pytz import timezone, UTC


class Users(models.Model):
    _inherit = 'res.users'

    calendar_default_privacy = fields.Selection(
        [('public', 'Public'),
         ('private', 'Private'),
         ('confidential', 'Only internal users')],
        compute="_compute_calendar_default_privacy",
        inverse="_inverse_calendar_res_users_settings",
    )

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

    @api.model_create_multi
    def create(self, vals_list):
        """ Set the calendar default privacy as the same as Default User Template when defined. """
        # Get the calendar default privacy from the Default User Template, set public as default.
        default_privacy = 'public'
        default_user = self.env.ref('base.default_user', raise_if_not_found=False)
        if default_user and default_user.calendar_default_privacy:
            default_privacy = default_user.calendar_default_privacy

        # Update the dictionaries in vals_list with the calendar default privacy.
        for vals_dict in vals_list:
            if not vals_dict.get('calendar_default_privacy'):
                vals_dict.update(calendar_default_privacy=default_privacy)

        res = super().create(vals_list)
        return res

    def write(self, vals):
        """ Forbid the calendar default privacy update from different users for keeping private events secured. """
        privacy_update = 'calendar_default_privacy' in vals
        default_user = self.env.ref('base.default_user', raise_if_not_found=False)
        if default_user and privacy_update and any(user not in [default_user, self.env.user] for user in self):
            raise AccessError(_("You are not allowed to change the calendar default privacy of another user due to privacy constraints."))
        res = super().write(vals)
        return res

    @api.depends("res_users_settings_id.calendar_default_privacy")
    def _compute_calendar_default_privacy(self):
        for user in self:
            user.calendar_default_privacy = user.res_users_settings_id.calendar_default_privacy

    def _inverse_calendar_res_users_settings(self):
        """
        Updates the values of the calendar fields in 'res_users_settings_ids' to have the same values as their related
        fields in 'res.users'. If there is no 'res.users.settings' record for the user, then the record is created.
        """
        for user in self:
            settings = self.env["res.users.settings"]._find_or_create_for_user(user)
            configuration = {field: user[field] for field in self._get_user_calendar_configuration_fields()}
            settings.update(configuration)

    @api.model
    def _get_user_calendar_configuration_fields(self) -> list[str]:
        """ Return the list of configurable fields for the user related to the res.users.settings table. """
        return ['calendar_default_privacy']

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
        stop_dt_utc = datetime.datetime.combine(start_dt_utc.date(), datetime.time.max).replace(tzinfo=UTC)

        tz = self.env.user.tz
        if tz:
            user_tz = timezone(tz)
            start_dt = start_dt_utc.astimezone(user_tz)
            stop_dt = datetime.datetime.combine(start_dt.date(), datetime.time.max).replace(tzinfo=user_tz)
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
