# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_compare


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _calculate_hours_per_week(self):
        self.ensure_one()
        sum_hours = sum(
            (a.hour_to - a.hour_from) for a in self.attendance_ids.filtered(lambda a: a.day_period != 'lunch'))
        return sum_hours / 2 if self.two_weeks_calendar else sum_hours

    def _calculate_is_fulltime(self):
        self.ensure_one()
        return not float_compare(self.full_time_required_hours, self._calculate_hours_per_week(), 3)
