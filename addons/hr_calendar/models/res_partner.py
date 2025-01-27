# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import UTC, timezone
from datetime import datetime
from collections import defaultdict
from functools import reduce

from odoo import api, models

from odoo.osv import expression
from odoo.addons.resource.models.utils import Intervals


class Partner(models.Model):
    _inherit = ['res.partner']

    def _get_employees_from_attendees(self, everybody=False):
        domain = [
            ('company_id', 'in', self.env.companies.ids),
            ('work_contact_id', '!=', False),
        ]
        if not everybody:
            domain = expression.AND([
                domain,
                [('work_contact_id', 'in', self.ids)]
            ])
        return dict(self.env['hr.employee'].sudo()._read_group(domain, groupby=['work_contact_id'], aggregates=['id:recordset']))

    def _get_schedule(self, start_period, stop_period, everybody=False, merge=True):
        """
        This method implements the general case where employees might have different resource calendars at different
        times, even though this is not the case with only this module installed.
        This way it will work with these other modules by just overriding
        `_get_calendar_periods`.

        :param datetime start_period: the start of the period
        :param datetime stop_period: the stop of the period
        :param boolean everybody: represents the "everybody" filter on calendar
        :param boolean merge: specifies if calendar's work_intervals needs to be merged
        :return: schedule (merged or not) by partner
        :rtype: defaultdict
        """
        employees_by_partner = self._get_employees_from_attendees(everybody)
        if not employees_by_partner:
            return {}
        interval_by_calendar = defaultdict()
        calendar_periods_by_employee = defaultdict(list)
        employees_by_calendar = defaultdict(list)

        # Compute employee's calendars's period and order employee by his involved calendars
        employees = sum(employees_by_partner.values(), start=self.env['hr.employee'])
        calendar_periods_by_employee = employees._get_calendar_periods(start_period, stop_period)
        for employee, calendar_periods in calendar_periods_by_employee.items():
            for (start, stop, calendar) in calendar_periods:
                employees_by_calendar[calendar].append(employee)

        # Compute all work intervals per calendar
        for calendar, employees in employees_by_calendar.items():
            calendar = calendar or self.env.company.resource_calendar_id # No calendar if fully flexible
            work_intervals = calendar._work_intervals_batch(start_period, stop_period, resources=employees, tz=timezone(calendar.tz))
            del work_intervals[False]
            # Merge all employees intervals to avoid to compute it multiples times
            if merge:
                interval_by_calendar[calendar] = reduce(Intervals.__and__, work_intervals.values())
            else:
                interval_by_calendar[calendar] = work_intervals

        # Compute employee's schedule based own his calendar's periods
        schedule_by_employee = defaultdict(list)
        for employee, calendar_periods in calendar_periods_by_employee.items():
            employee_interval = Intervals([])
            for (start, stop, calendar) in calendar_periods:
                calendar = calendar or self.env.company.resource_calendar_id # No calendar if fully flexible
                interval = Intervals([(start, stop, self.env['resource.calendar'])])
                if merge:
                    calendar_interval = interval_by_calendar[calendar]
                else:
                    calendar_interval = interval_by_calendar[calendar][employee.id]
                employee_interval = employee_interval | (calendar_interval & interval)
            schedule_by_employee[employee] = employee_interval

        # Compute partner's schedule equals to the union between his employees's schedule
        schedules = defaultdict()
        for partner, employees in employees_by_partner.items():
            partner_schedule = Intervals([])
            for employee in employees:
                if schedule_by_employee[employee]:
                    partner_schedule = partner_schedule | schedule_by_employee[employee]
            schedules[partner] = partner_schedule
        return schedules

    @api.model
    def get_working_hours_for_all_attendees(self, attendee_ids, date_from, date_to, everybody=False):

        start_period = datetime.fromisoformat(date_from).replace(hour=0, minute=0, second=0, tzinfo=UTC)
        stop_period = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=UTC)

        schedule_by_partner = self.env['res.partner'].browse(attendee_ids)._get_schedule(start_period, stop_period, everybody)
        if not schedule_by_partner:
            return []
        return self._interval_to_business_hours(reduce(Intervals.__and__, schedule_by_partner.values()))

    def _interval_to_business_hours(self, working_intervals):
        # This is the format expected by the fullcalendar library to do the overlay
        return [{
            "daysOfWeek": [(interval[0].weekday() + 1) % 7],
            "startTime":  interval[0].astimezone(timezone(self.env.user.tz or 'UTC')).strftime("%H:%M"),
            "endTime": interval[1].astimezone(timezone(self.env.user.tz or 'UTC')).strftime("%H:%M"),
        } for interval in working_intervals] if working_intervals else [{
            # 7 is used a dummy value to gray the full week
            # Returning an empty list would leave the week uncolored
            "daysOfWeek": [7],
            "startTime":  datetime.today().strftime("00:00"),
            "endTime": datetime.today().strftime("00:00"),
        }]
