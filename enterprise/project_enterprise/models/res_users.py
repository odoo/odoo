# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import models
from odoo.addons.resource.models.utils import Intervals

class User(models.Model):
    _inherit = 'res.users'

    # -----------------------------------------
    # Business Methods
    # -----------------------------------------
    def _get_calendars_validity_within_period(self, start, end):
        """ Gets a dict of dict with user's id as first key and user's calendar as secondary key
            The value is the validity interval of the calendar for the given user.

            Here the validity interval for each calendar is the whole interval but it's meant to be overriden in further modules
            handling user's employee contracts.
        """
        assert start.tzinfo and end.tzinfo
        user_resources = {user: user._get_project_task_resource() for user in self}
        user_calendars_within_period = defaultdict(lambda: defaultdict(Intervals))  # keys are [user id:integer][calendar:self.env['resource.calendar']]
        resource_calendars_within_period = self._get_project_task_resource()._get_calendars_validity_within_period(start, end)
        if not self:
            # if no user, add the company resource calendar.
            user_calendars_within_period[False] = resource_calendars_within_period[False]
        for user, resource in user_resources.items():
            if resource:
                user_calendars_within_period[user.id] = resource_calendars_within_period[resource.id]
            else:
                calendar = user.resource_calendar_id or user.company_id.resource_calendar_id or self.env.company.resource_calendar_id
                user_calendars_within_period[user.id][calendar] = Intervals([(start, end, self.env['resource.calendar.attendance'])])
        return user_calendars_within_period

    def _get_valid_work_intervals(self, start, end, calendars=None):
        """ Gets the valid work intervals of the user following their calendars between ``start`` and ``end``

            This methods handle the eventuality of a user's resource having multiple resource calendars,
            see _get_calendars_validity_within_period method for further explanation.
        """
        assert start.tzinfo and end.tzinfo
        user_calendar_validity_intervals = {}
        calendar_users = defaultdict(lambda: self.env['res.users'])
        user_work_intervals = defaultdict(Intervals)
        calendar_work_intervals = dict()
        user_resources = {user: user._get_project_task_resource() for user in self}

        user_calendar_validity_intervals = self._get_calendars_validity_within_period(start, end)
        for user in self:
            # For each user, retrieve its calendar and their validity intervals
            for calendar in user_calendar_validity_intervals[user.id]:
                calendar_users[calendar] |= user
        for calendar in (calendars or []):
            calendar_users[calendar] |= self.env['res.users']
        for calendar, users in calendar_users.items():
            # For each calendar used by the users, retrieve the work intervals for every users using it
            if not calendar:
                continue
            work_intervals_batch = calendar._work_intervals_batch(start, end, resources=users._get_project_task_resource())
            for user in users:
                # Make the conjunction between work intervals and calendar validity
                user_work_intervals[user.id] |= work_intervals_batch[user_resources[user].id] & user_calendar_validity_intervals[user.id][calendar]
            calendar_work_intervals[calendar.id] = work_intervals_batch[False]

        return user_work_intervals, calendar_work_intervals

    def _get_project_task_resource(self):
        return self.env['resource.resource']
