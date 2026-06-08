# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time
from functools import reduce
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, models
from odoo.fields import Domain
from odoo.tools.intervals import Intervals


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_employees_from_attendees(self):
        domain = (
            Domain('company_id', 'in', self.env.companies.ids)
            & Domain('work_contact_id', '!=', False)
            & Domain("work_contact_id", "in", self.ids)
        )
        return dict(self.env['hr.employee'].sudo()._read_group(domain, groupby=['work_contact_id'], aggregates=['id:recordset']))

    def _get_schedule(self, start_period, stop_period, merge=True):
        """
        This method implements the general case where employees might have different resource calendars at different
        times, even though this is not the case with only this module installed.
        This way it will work with these other modules by just overriding
        `_get_calendar_periods`.

        :param datetime start_period: the start of the period
        :param datetime stop_period: the stop of the period
        :param boolean merge: specifies if calendar's work_intervals needs to be merged
        :return: schedule (merged or not) by partner
        :rtype: defaultdict
        """
        employees_by_partner = self._get_employees_from_attendees()
        if not employees_by_partner:
            return {}
        interval_by_calendar = defaultdict()
        resources_by_calendar = defaultdict(lambda: self.env['resource.resource'])

        # Compute employee's calendars's period and order employee by his involved calendars
        employees = sum(employees_by_partner.values(), start=self.env['hr.employee'])
        calendar_periods_by_employee = employees._get_calendar_periods(start_period.date(), stop_period.date())
        for employee, calendar_periods in calendar_periods_by_employee.items():
            for _start, _stop, calendar in calendar_periods:
                calendar = calendar or self.env.company.resource_calendar_id
                resources_by_calendar[calendar] += employee.resource_id

        # Compute all work intervals per calendar
        for calendar, resources in resources_by_calendar.items():
            resources_per_tz = resources._get_resources_per_tz()
            work_intervals = calendar._work_intervals_batch(start_period, stop_period, resources_per_tz=resources_per_tz)
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
                tz = ZoneInfo(employee._get_tz(start))
                interval = Intervals([(
                    datetime.combine(start, time.min, tz),
                    datetime.combine(stop, time.max, tz),
                    self.env['resource.calendar'])])
                if merge:
                    calendar_interval = interval_by_calendar[calendar]
                else:
                    calendar_interval = interval_by_calendar[calendar][employee.resource_id.id]
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
    def get_working_hours_for_all_attendees(self, attendee_ids, date_from, date_to):
        timezone = ZoneInfo(self.env.user.tz or "UTC")
        start_period = datetime.fromisoformat(date_from).replace(hour=0, minute=0, second=0, tzinfo=timezone)
        stop_period = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone)

        offset = relativedelta(days=1)
        schedule_by_partner = (
            self.env["res.partner"]
            .browse(attendee_ids)
            ._get_schedule(
                start_period - offset,  # We use an 1 day offset to capture work entries that start the day before
                stop_period + offset,  # We use an 1 day offset to capture work entries that span into the day after
            )
        )
        if not schedule_by_partner:
            return []
        return self._interval_to_business_hours(
            reduce(Intervals.__and__, schedule_by_partner.values()),
            start_period,
            stop_period,
        )

    @api.model
    def get_working_days_for_all_attendees(self, attendee_ids, date_from, date_to):
        timezone = ZoneInfo(self.env.user.tz or "UTC")
        start_period = datetime.fromisoformat(date_from).replace(hour=0, minute=0, second=0, tzinfo=timezone)
        stop_period = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone)

        offset = relativedelta(days=1)
        schedule_by_partner = (
            self.env["res.partner"]
            .browse(attendee_ids)
            ._get_schedule(
                start_period - offset,  # We use an 1 day offset to capture work entries that start the day before
                stop_period + offset,  # We use an 1 day offset to capture work entries that span into the day after
            )
        )
        return self._intervals_to_business_days(reduce(Intervals.__and__, schedule_by_partner.values()))

    @api.model
    def _interval_to_business_hours(self, working_intervals, start_period, stop_period):
        if not working_intervals:
            return [self._format_fullcalendar_business_hours()]

        business_hours = []
        for working_interval in working_intervals:
            localized_start_datetime = working_interval[0].astimezone(ZoneInfo(self.env.user.tz or "UTC"))
            localized_end_datetime = working_interval[1].astimezone(ZoneInfo(self.env.user.tz or "UTC"))

            if localized_end_datetime <= start_period or localized_start_datetime >= stop_period:
                continue

            clamped_start_datetime = max(localized_start_datetime, start_period)
            clamped_end_datetime = min(localized_end_datetime, stop_period)

            start_date = clamped_start_datetime.date()
            end_date = clamped_end_datetime.date()
            if start_date == end_date:
                business_hours.append(
                    self._format_fullcalendar_business_hours(
                        weekday=(clamped_start_datetime.weekday() + 1) % 7,
                        start_time=clamped_start_datetime.strftime("%H:%M"),
                        end_time=clamped_end_datetime.strftime("%H:%M"),
                    ),
                )
            else:
                # Multi-day interval
                # Handle first day
                first_day_end = datetime.combine(start_date, time.max, tzinfo=ZoneInfo(self.env.user.tz or "UTC"))
                if clamped_start_datetime < first_day_end:
                    business_hours.append(
                        self._format_fullcalendar_business_hours(
                            weekday=(clamped_start_datetime.weekday() + 1) % 7,
                            start_time=clamped_start_datetime.strftime("%H:%M"),
                            end_time="23:59",
                        ),
                    )

                # Handle middle days (if any full days between start and end)
                if (end_date - start_date).days > 1:
                    current_day = start_date + relativedelta(days=1)
                    while current_day < end_date:
                        business_hours.append(
                            self._format_fullcalendar_business_hours(
                                weekday=(current_day.weekday() + 1) % 7,
                                start_time="00:00",
                                end_time="23:59",
                            ),
                        )
                        current_day += relativedelta(days=1)

                # Handle last day
                last_day_start = datetime.combine(end_date, time.min, tzinfo=ZoneInfo(self.env.user.tz or "UTC"))
                if last_day_start < clamped_end_datetime:
                    end_time = clamped_end_datetime.strftime("%H:%M")
                    if end_time != "00:00":
                        business_hours.append(
                            self._format_fullcalendar_business_hours(
                                weekday=(clamped_end_datetime.weekday() + 1) % 7,
                                start_time="00:00",
                                end_time=end_time,
                            ),
                        )

        return business_hours

    @api.model
    def _intervals_to_business_days(self, working_intervals):
        working_days = set()
        for interval in working_intervals:
            localized_start_date = interval[0].astimezone(ZoneInfo(self.env.user.tz or "UTC")).date()
            localized_end_date = interval[1].astimezone(ZoneInfo(self.env.user.tz or "UTC")).date()
            working_days.add(localized_start_date)
            if localized_start_date != localized_end_date:
                middle_day = localized_start_date + relativedelta(days=1)
                while middle_day <= localized_end_date:
                    working_days.add(middle_day)
                    middle_day += relativedelta(days=1)

        return working_days

    @api.model
    def _format_fullcalendar_business_hours(self, weekday=7, start_time="00:00", end_time="00:00"):
        """
        Format business hours values for Fullcalendar so it can grey out unavailable slots in the calendar.

        Fullcalendar is a library that is used by the calendar view. It expects a specifically formatted dictionary for
        the business hours API option to properly grey out areas where an employee is not available. If an employee has
        no intervals we return the default values, with weekday=7 as a dummy value to grey out the entire week.
        Returning nothing would leave the calendar completely uncolored.

        :param int weekday: Day of week (0-6 for Mon-Sun, 7 as dummy to grey entire week). Defaults to 7.
        :param string start_time: Start time in "HH:MM" format. Defaults to "00:00".
        :param string end_time: End time in "HH:MM" format. Defaults to "00:00".

        :return: Fullcalendar-business-hours-configuration dict with the keys 'daysOfWeek', 'startTime', and 'endTime'.
        :rtype: dict
        """
        return {
            "daysOfWeek": [weekday],
            "startTime": start_time,
            "endTime": end_time,
        }

    @api.model
    def _get_unusual_days(self, attendee_ids, date_from, date_to):
        timezone = ZoneInfo(self.env.user.tz or "UTC")
        start_period = datetime.fromisoformat(date_from).replace(hour=0, minute=0, second=0, tzinfo=timezone)
        stop_period = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=timezone)

        working_days = self.get_working_days_for_all_attendees(attendee_ids, date_from, date_to)

        return {
            day.strftime("%Y-%m-%d"): (day.date() not in working_days)
            for day in rrule(DAILY, start_period, until=stop_period)
        }

    def get_worklocation(self, start_date, end_date):
        employee_id = self.env['hr.employee'].search([
            ('work_contact_id.id', 'in', self.ids),
            ('company_id.id', '=', self.env.company.id)])
        return employee_id._get_worklocation(start_date, end_date)
