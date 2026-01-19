# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from collections import defaultdict
from datetime import datetime, time, timedelta, UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import ormcache, float_is_zero
from odoo.tools.intervals import Intervals


class HrVersion(models.Model):
    _inherit = 'hr.version'

    work_entry_source = fields.Selection([('calendar', 'Working Schedule')], required=True, default='calendar', tracking=True, help='''
        Defines the source for work entries generation

        Working Schedule: Work entries will be generated from the working hours below.
        Attendances: Work entries will be generated from the employee's attendances. (requires Attendance app)
        Planning: Work entries will be generated from the employee's planning. (requires Planning app)
    ''', groups="base.group_system,hr.group_hr_manager")
    work_entry_source_calendar_invalid = fields.Boolean(
        compute='_compute_work_entry_source_calendar_invalid',
        groups="hr.group_hr_manager",
    )

    @api.depends('work_entry_source', 'resource_calendar_id')
    def _compute_work_entry_source_calendar_invalid(self):
        for version in self:
            version.work_entry_source_calendar_invalid = version.work_entry_source == 'calendar' and not version.resource_calendar_id

    # YTI Break ormcache + select country attendance entry type
    @ormcache()
    def _get_default_work_entry_type_id(self):
        attendance = self.env.ref('hr_work_entry.generic_work_entry_type_attendance', raise_if_not_found=False)
        return attendance.id if attendance else False

    def _get_leave_work_entry_type_dates(self, leave, date_from, date_to, employee):
        return self._get_leave_work_entry_type(leave)

    def _get_leave_work_entry_type(self, leave):
        return leave.work_entry_type_id

    # Is used to add more values, for example planning_slot_id
    def _get_more_vals_attendance_interval(self, interval):
        return []

    # Is used to add more values, for example leave_id (in hr_holidays)
    def _get_more_vals_leave_interval(self, interval, leaves):
        return []

    def _get_bypassing_work_entry_type_codes(self):
        return []

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        # returns the work entry time related to the leave that
        # includes the whole interval.
        # Overriden in hr_work_entry_holiday to select the
        # global time off first (eg: Public Holiday > Home Working)
        self.ensure_one()
        for leave in leaves:
            if interval[0] >= leave[0] and interval[1] <= leave[1] and leave[2]:
                interval_start = interval[0].astimezone(UTC).replace(tzinfo=None)
                interval_stop = interval[1].astimezone(UTC).replace(tzinfo=None)
                return self._get_leave_work_entry_type_dates(leave[2], interval_start, interval_stop, self.employee_id)
        return self.env.ref('hr_work_entry.generic_work_entry_type_leave')

    def _get_sub_leave_domain(self):
        return Domain('calendar_id', 'in', [False] + self.resource_calendar_id.ids)

    def _get_leave_domain(self, start_dt, end_dt):
        domain = Domain([
            ('resource_id', 'in', [False] + self.employee_id.resource_id.ids),
            ('date_from', '<=', end_dt.replace(tzinfo=None)),
            ('date_to', '>=', start_dt.replace(tzinfo=None)),
            ('company_id', 'in', [False] + self.env.companies.ids),
        ])
        return domain & self._get_sub_leave_domain()

    def _get_resource_calendar_leaves(self, start_dt, end_dt):
        return self.env['resource.calendar.leaves'].search(self._get_leave_domain(start_dt, end_dt))

    def _get_attendance_intervals(self, start_dt, end_dt):
        assert start_dt.tzinfo and end_dt.tzinfo, "function expects localized date"
        # {resource: intervals}
        versions_with_calendar_work_entry_source = self.filtered(lambda version: version.work_entry_source == 'calendar')
        result = dict()
        for calendar, versions in versions_with_calendar_work_entry_source.grouped('resource_calendar_id').items():
            fully_flex_versions = versions.filtered('is_fully_flexible')
            for version in fully_flex_versions:
                result.update({version.employee_id.resource_id.id: Intervals([(start_dt, end_dt, self.env['resource.calendar.attendance'])])})
            remaining_versions = (versions - fully_flex_versions).with_prefetch()
            resources_per_tz = remaining_versions._get_resources_per_tz()
            if remaining_versions:
                result.update(calendar._attendance_intervals_batch(
                    start_dt,
                    end_dt,
                    resources_per_tz=resources_per_tz,
                ))
        return result

    def _get_interval_work_entry_type(self, interval):
        self.ensure_one()
        if 'work_entry_type_id' in interval[2] and interval[2].work_entry_type_id[:1]:
            return interval[2].work_entry_type_id[:1]
        return self.env['hr.work.entry.type'].browse(self._get_default_work_entry_type_id())

    def _get_valid_leave_intervals(self, attendances, interval):
        self.ensure_one()
        return [interval]

    @api.model
    def _get_whitelist_fields_from_template(self):
        return super()._get_whitelist_fields_from_template() + ['work_entry_source']

    # Meant for behavior override
    def _get_real_attendance_work_entry_vals(self, intervals):
        self.ensure_one()
        vals = []
        employee = self.employee_id
        for interval in intervals:
            work_entry_type = self._get_interval_work_entry_type(interval)
            # All benefits generated here are using datetimes converted from the employee's timezone
            vals += [dict([
                      ('date_start', interval[0].astimezone(UTC).replace(tzinfo=None)),
                      ('date_stop', interval[1].astimezone(UTC).replace(tzinfo=None)),
                      ('work_entry_type_id', work_entry_type),
                      ('employee_id', employee),
                      ('version_id', self),
                      ('company_id', self.company_id),
                  ] + self._get_more_vals_attendance_interval(interval))]
        return vals

    def _get_version_work_entries_values(self, date_start, date_stop):
        start_dt = date_start.replace(tzinfo=UTC) if not date_start.tzinfo else date_start
        end_dt = date_stop.replace(tzinfo=UTC) if not date_stop.tzinfo else date_stop
        version_vals = []
        bypassing_work_entry_type_codes = self._get_bypassing_work_entry_type_codes()

        expected_attendances_by_resource = self.sudo()._get_attendance_intervals(start_dt, end_dt)

        resource_calendar_leaves = self._get_resource_calendar_leaves(start_dt, end_dt)
        # {resource: resource_calendar_leaves}
        all_leaves_by_resource = defaultdict(lambda: self.env['resource.calendar.leaves'])
        for leave in resource_calendar_leaves:
            all_leaves_by_resource[leave.resource_id.id] |= leave

        tz_dates = {}
        for version in self:
            employee = version.employee_id
            calendar = version.resource_calendar_id
            resource = employee.resource_id
            tz = ZoneInfo(version._get_tz())
            expected_attendances = expected_attendances_by_resource[resource.id]

            # Other calendars: In case the employee has declared time off in another calendar
            # Example: Take a time off, then a credit time.
            resources_list = [self.env['resource.resource'], resource]
            leave_result = defaultdict(list)
            work_result = defaultdict(list)
            for leave in itertools.chain(all_leaves_by_resource[False], all_leaves_by_resource[resource.id]):
                for resource in resources_list:
                    # Global time off is not for this calendar, can happen with multiple calendars in self
                    if resource and leave.calendar_id and leave.calendar_id != calendar and not leave.resource_id:
                        continue
                    tz = tz if tz else ZoneInfo((resource or version).tz)
                    if (tz, start_dt) in tz_dates:
                        start = tz_dates[tz, start_dt]
                    else:
                        start = start_dt.astimezone(tz)
                        tz_dates[tz, start_dt] = start
                    if (tz, end_dt) in tz_dates:
                        end = tz_dates[tz, end_dt]
                    else:
                        end = end_dt.astimezone(tz)
                        tz_dates[tz, end_dt] = end
                    dt0 = leave.date_from.astimezone(tz)
                    dt1 = leave.date_to.astimezone(tz)
                    leave_start_dt = max(start, dt0)
                    leave_end_dt = min(end, dt1)
                    leave_interval = (leave_start_dt, leave_end_dt, leave)
                    leave_interval = version._get_valid_leave_intervals(expected_attendances, leave_interval)
                    if leave_interval:
                        if leave.count_as == 'absence':
                            leave_result[resource.id] += leave_interval
                        else:
                            work_result[resource.id] += leave_interval
            leaves_by_resource = {r.id: Intervals(leave_result[r.id], keep_distinct=True) for r in resources_list}
            worked_leaves_by_resource = {r.id: Intervals(work_result[r.id], keep_distinct=True) for r in resources_list}

            leaves = leaves_by_resource[resource.id]
            worked_leaves = worked_leaves_by_resource[resource.id]

            real_attendances = expected_attendances - leaves - worked_leaves
            if version.is_fully_flexible:
                real_leaves = leaves
            elif version.is_flexible:
                # Flexible hours case
                # For multi day leaves, we want them to occupy the virtual working schedule 12 AM to average working days
                # For one day leaves, we want them to occupy exactly the time it was taken, for a time off in days
                # this will mean the virtual schedule and for time off in hours the chosen hours
                one_day_leaves = Intervals([l for l in leaves if l[0].astimezone(tz).date() == l[1].astimezone(tz).date()], keep_distinct=True)
                multi_day_leaves = leaves - one_day_leaves
                resources_per_tz = version._get_resources_per_tz()
                static_attendances = calendar._attendance_intervals_batch(
                    start_dt, end_dt, resources_per_tz=resources_per_tz)[resource.id]
                real_leaves = (static_attendances & multi_day_leaves) | one_day_leaves
            elif version.has_static_work_entries() or not leaves:
                real_leaves = expected_attendances & leaves
            else:
                resources_per_tz = version._get_resources_per_tz()
                static_attendances = calendar._attendance_intervals_batch(
                    start_dt, end_dt, resources_per_tz=resources_per_tz)[resource.id]
                real_leaves = static_attendances & leaves

            real_worked_leaves = worked_leaves - real_leaves
            real_attendances = self._get_real_attendances(expected_attendances, leaves, worked_leaves)

            # A leave period can be linked to several resource.calendar.leave
            split_leaves = []
            for leave_interval in leaves:
                if leave_interval[2] and len(leave_interval[2]) > 1:
                    split_leaves += [(leave_interval[0], leave_interval[1], l) for l in leave_interval[2]]
                else:
                    split_leaves += [(leave_interval[0], leave_interval[1], leave_interval[2])]
            leaves = split_leaves

            split_worked_leaves = []
            for worked_leave_interval in real_worked_leaves:
                if worked_leave_interval[2] and len(worked_leave_interval[2]) > 1:
                    split_worked_leaves += [(worked_leave_interval[0], worked_leave_interval[1], l) for l in worked_leave_interval[2]]
                else:
                    split_worked_leaves += [(worked_leave_interval[0], worked_leave_interval[1], worked_leave_interval[2])]
            real_worked_leaves = split_worked_leaves

            # Attendances
            version_vals += version._get_real_attendance_work_entry_vals(real_attendances)

            for interval in real_worked_leaves:
                work_entry_type = version._get_interval_leave_work_entry_type(interval, worked_leaves, bypassing_work_entry_type_codes)
                # All benefits generated here are using datetimes converted from the employee's timezone
                version_vals += [dict([
                    ('date_start', interval[0].astimezone(UTC).replace(tzinfo=None)),
                    ('date_stop', interval[1].astimezone(UTC).replace(tzinfo=None)),
                    ('work_entry_type_id', work_entry_type),
                    ('employee_id', employee),
                    ('version_id', version),
                    ('company_id', version.company_id),
                ] + version._get_more_vals_leave_interval(interval, worked_leaves))]

            leaves_over_attendances = Intervals(leaves, keep_distinct=True) & real_leaves
            for interval in real_leaves:
                # Could happen when a leave is configured on the interface on a day for which the
                # employee is not supposed to work, i.e. no attendance_ids on the calendar.
                # In that case, do try to generate an empty work entry, as this would raise a
                # sql constraint error
                if interval[0] == interval[1]:  # if start == stop
                    continue
                leaves_over_interval = [l for l in leaves_over_attendances if l[0] >= interval[0] and l[1] <= interval[1]]
                for leave_interval in [(l[0], l[1], interval[2]) for l in leaves_over_interval]:
                    leave_entry_type = version._get_interval_leave_work_entry_type(leave_interval, leaves, bypassing_work_entry_type_codes)
                    # leaves don't have work_entry_type_id set if you create them before having hr_work_entry_installed
                    interval_leaves = [leave for leave in leaves if not leave[2].work_entry_type_id or leave[2].work_entry_type_id.id == leave_entry_type.id]
                    if not interval_leaves:
                        # Maybe the computed leave type is not found. In that case, we use all leaves
                        interval_leaves = leaves
                    interval_start = leave_interval[0].astimezone(UTC).replace(tzinfo=None)
                    interval_stop = leave_interval[1].astimezone(UTC).replace(tzinfo=None)
                    version_vals += [dict([
                        ('date_start', interval_start),
                        ('date_stop', interval_stop),
                        ('work_entry_type_id', leave_entry_type),
                        ('employee_id', employee),
                        ('company_id', version.company_id),
                        ('version_id', version),
                    ] + version._get_more_vals_leave_interval(interval, interval_leaves))]
        return version_vals

    # will override in attendance bridge to add overtime vals
    def _get_real_attendances(self, attendances, leaves, worked_leaves):
        return attendances - leaves - worked_leaves

    def _get_work_entries_values(self, date_start, date_stop):
        """
        Generate a work_entries list between date_start and date_stop for one version.
        :return: list of dictionnary.
        """
        if isinstance(date_start, datetime):
            version_vals = self._get_version_work_entries_values(date_start, date_stop)
        else:
            version_vals = []
            versions_by_tz = defaultdict(lambda: self.env['hr.version'])
            for version in self:
                versions_by_tz[version._get_tz()] += version
            for version_tz, versions in versions_by_tz.items():
                tz = ZoneInfo(version_tz) if version_tz else UTC
                version_vals += versions._get_version_work_entries_values(
                    date_start.replace(tzinfo=tz),
                    date_stop.replace(tzinfo=tz))

        return version_vals

    def has_static_work_entries(self):
        # Static work entries as in the same are to be generated each month
        # Useful to differentiate attendance based versions from regular ones
        self.ensure_one()
        return self.work_entry_source == 'calendar'

    def generate_work_entries(self, date_start, date_stop):
        # Generate work entries between 2 dates (datetime.date)
        # To correctly englobe the period, the start and end periods are converted
        # using the calendar timezone.
        assert not isinstance(date_start, datetime)
        assert not isinstance(date_stop, datetime)

        date_start = datetime.combine(fields.Datetime.to_datetime(date_start), datetime.min.time())
        date_stop = datetime.combine(fields.Datetime.to_datetime(date_stop), datetime.max.time())

        versions_by_company_tz = defaultdict(lambda: self.env['hr.version'])
        for version in self:
            versions_by_company_tz[
                version.company_id,
                version.tz or version.employee_id.user_id.tz,
            ] += version
        new_work_entries = []
        for (company, version_tz), versions in versions_by_company_tz.items():
            tz = ZoneInfo(version_tz) if version_tz else UTC
            date_start_tz = date_start.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
            date_stop_tz = date_stop.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
            new_work_entries += versions.with_user(SUPERUSER_ID).with_company(company)._generate_work_entries(
                date_start_tz, date_stop_tz)
        return new_work_entries

    def _generate_work_entries(self, date_start, date_stop):
        # Generate work entries between 2 dates (datetime.datetime)
        # This method considers that the dates are correctly localized
        # based on the target timezone
        assert isinstance(date_start, datetime)
        assert isinstance(date_stop, datetime)
        self = self.with_context(tracking_disable=True)  # noqa: PLW0642
        vals_list = []

        intervals_to_generate = defaultdict(lambda: self.env['hr.version'])

        for tz, versions in self.grouped("tz").items():
            tz = ZoneInfo(tz) if tz else UTC
            for version in versions:
                version_start = fields.Datetime.to_datetime(version.date_start).replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                version_stop = datetime.combine(fields.Datetime.to_datetime(version.date_end or date_stop),
                                                 datetime.max.time()).replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                if version_stop < date_start:
                    continue
                if date_start > version_stop or date_stop < version_start:
                    continue
                date_start_work_entries = max(date_start, version_start)
                date_stop_work_entries = min(date_stop, version_stop)
                intervals_to_generate[date_start_work_entries, date_stop_work_entries] |= version

        for interval, versions in intervals_to_generate.items():
            date_from, date_to = interval
            vals_list.extend(versions._get_work_entries_values(date_from, date_to))

        if not vals_list:
            return vals_list

        vals_list = self._generate_work_entries_postprocess(vals_list)
        return vals_list

    @api.model
    def _get_work_entry_source_fields(self):
        """
        Returns the list of work entry fields that should be merged/aggregated
        when combining multiple work entries of the same type.

        This is used in _generate_work_entries_postprocess to properly handle
        source-specific fields (e.g., leave_ids, attendance_ids, planning_slot_ids)
        when merging work entries.

        :return: list of field names to aggregate
        """
        return []

    @api.model
    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        if 'work_entry_type_id' not in vals:
            return False
        work_entry_type = vals['work_entry_type_id']
        return work_entry_type.count_as == 'absence'

    @api.model
    def _generate_work_entries_postprocess(self, vals_list):
        # Convert date_start/date_stop to date/duration
        # Split work entries over 2 days due to timezone conversion
        # Regroup work entries of the same type
        mapped_periods = defaultdict(lambda: defaultdict(lambda: self.env['hr.employee']))
        cached_periods = defaultdict(float)
        tz_by_version = {}

        def _get_tz(version):
            if version in tz_by_version:
                return tz_by_version[version]
            tz = version._get_tz()
            if not tz:
                raise UserError(_('Missing timezone for work entries generation.'))
            tz = ZoneInfo(tz)
            tz_by_version[version] = tz
            return tz

        new_vals_list = []
        for vals in vals_list:
            new_vals = vals.copy()
            if not new_vals.get('date_start') or not new_vals.get('date_stop'):
                new_vals.pop('date_start', False)
                new_vals.pop('date_stop', False)
                if 'duration' not in new_vals or 'date' not in new_vals:
                    raise UserError(_('Missing date or duration on work entry'))
                new_vals_list.append(new_vals)
                continue

            date_start_utc = new_vals['date_start'] if new_vals['date_start'].tzinfo else new_vals['date_start'].replace(tzinfo=UTC)
            date_stop_utc = new_vals['date_stop'] if new_vals['date_stop'].tzinfo else new_vals['date_stop'].replace(tzinfo=UTC)

            tz = _get_tz(new_vals['version_id'])
            local_start = date_start_utc.astimezone(tz)
            local_stop = date_stop_utc.astimezone(tz)

            # Handle multi-local-day spans
            current = local_start + timedelta(microseconds=1) if local_start.time() == datetime.max.time() else local_start
            while current < local_stop:
                next_local_midnight = (datetime.combine(current.date() + timedelta(days=1), time.min) - timedelta(microseconds=1)).replace(tzinfo=tz)
                segment_end = min(local_stop, next_local_midnight)

                partial_vals = new_vals.copy()

                # Convert partial segment back to UTC for consistency
                partial_vals['date_start'] = current.astimezone(UTC)
                partial_vals['date_stop'] = segment_end.astimezone(UTC)

                new_vals_list.append(partial_vals)

                current = segment_end + timedelta(microseconds=1)

        vals_list = new_vals_list

        for vals in vals_list:
            if not vals.get('date_start') or not vals.get('date_stop'):
                continue
            date_start = vals['date_start']
            date_stop = vals['date_stop']
            tz = _get_tz(vals['version_id'])
            if not self._generate_work_entries_postprocess_adapt_to_calendar(vals):
                vals['date'] = date_start.astimezone(tz).date()
                if 'duration' in vals:
                    continue
                elif (date_start, date_stop) in cached_periods:
                    vals['duration'] = cached_periods[date_start, date_stop]
                else:
                    dt = date_stop - date_start
                    duration = round(dt.total_seconds()) / 3600  # Number of hours
                    cached_periods[date_start, date_stop] = duration
                    vals['duration'] = duration
                continue
            version = vals['version_id']
            calendar = version.resource_calendar_id
            if not calendar and not version.hours_per_week and not version.hours_per_day:
                vals['date'] = date_start.astimezone(tz).date()
                vals['duration'] = 0.0
                continue
            employee = version.employee_id
            mapped_periods[date_start, date_stop][calendar] |= employee

        # {(date_start, date_stop): {calendar: {'hours': foo}}}
        mapped_version_data = defaultdict(lambda: defaultdict(lambda: {'hours': 0.0}))
        for (date_start, date_stop), employees_by_calendar in mapped_periods.items():
            for calendar, employees in employees_by_calendar.items():
                mapped_version_data[date_start, date_stop][calendar] = employees._get_work_days_data_batch(
                    date_start, date_stop, compute_leaves=False, calendar=calendar)

        for vals in vals_list:
            if 'duration' not in vals:
                date_start = vals['date_start']
                date_stop = vals['date_stop']
                version = vals['version_id']
                calendar = version.resource_calendar_id
                hours_per_week = version.hours_per_week
                hours_per_day = version.hours_per_day
                employee = version.employee_id
                tz = _get_tz(version)
                vals['date'] = date_start.astimezone(tz).date()
                vals['duration'] = mapped_version_data[date_start, date_stop][calendar][employee.id]['hours'] if calendar or hours_per_week or hours_per_day else 0.0
            vals.pop('date_start', False)
            vals.pop('date_stop', False)

        # Now merge similar work entries on the same day
        merged_vals = {}
        for vals in vals_list:
            if float_is_zero(vals['duration'], 3):
                continue
            key = (
                vals['date'],
                vals.get('work_entry_type_id', False),
                vals['employee_id'],
                vals['version_id'],
                vals.get('company_id', False),
            )
            if key in merged_vals:
                merged_vals[key]['duration'] += vals.get('duration', 0.0)
                source_fields = self._get_work_entry_source_fields()
                for field in source_fields:
                    if field in merged_vals[key] and field in vals:
                        merged_vals[key][field] |= vals[field]
            else:
                merged_vals[key] = vals.copy()
        return list(merged_vals.values())
