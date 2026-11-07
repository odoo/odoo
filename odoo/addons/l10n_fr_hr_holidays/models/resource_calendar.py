# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import ormcache

from collections import defaultdict


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _works_on_date(self, date):
        self.ensure_one()

        working_days = self._get_working_hours()
        dayofweek = str(date.weekday())
        if self.two_weeks_calendar:
            weektype = str(self.env['resource.calendar.attendance'].get_week_type(date))
            return working_days[weektype][dayofweek]
        return working_days[False][dayofweek]

    @ormcache('self.id')
    def _get_working_hours(self):
        self.ensure_one()

        working_days = defaultdict(lambda: defaultdict(lambda: False))
        for attendance in self.attendance_ids:
            working_days[attendance.week_type][attendance.dayofweek] = True
        return working_days
