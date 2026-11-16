# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, time, timedelta, UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import float_is_zero
from odoo.tools.date_utils import localized
from odoo.tools.intervals import Intervals


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def _get_default_work_entry_type_id(self):
        """Return the id of the work entry type used for worked time without explicit type.

        Used for calendar attendances without ``work_entry_type_id`` and for attendances
        without type. Default: the ``002.00`` type of the version's country, else the generic
        ``hr_work_entry.generic_work_entry_type_attendance``. ``hr_payroll`` gives precedence to
        the structure type's ``default_work_entry_type_id``.

        :return: an ``hr.work.entry.type`` id, or ``False`` if none is found
        :rtype: int
        """
        country_code = self.country_code
        country_attendance = self.env['hr.work.entry.type'].search([
            ('code', '=', '002.00'),
            ('country_code', '=', country_code),
        ], limit=1)
        attendance = country_attendance or self.env.ref('hr_work_entry.generic_work_entry_type_attendance', raise_if_not_found=False)
        return attendance.id if attendance else False

    def _get_leave_work_entry_type_dates(self, leave, date_from, date_to, employee):
        """Return the work entry type of ``leave`` for the slice ``[date_from, date_to]``.

        Override to make the type depend on the period, e.g. ``l10n_be_hr_payroll`` switches
        a sick leave to another type after 30 days. Default: :meth:`_get_leave_work_entry_type`.

        :param leave: the ``resource.calendar.leaves`` record covering the slice
        :param datetime date_from: slice start, naive UTC
        :param datetime date_to: slice end, naive UTC
        :param employee: the ``hr.employee`` of the version
        :rtype: hr.work.entry.type
        """
        return self._get_leave_work_entry_type(leave)

    def _get_leave_work_entry_type(self, leave):
        """Return the work entry type of a ``resource.calendar.leaves`` record.

        ``hr_holidays`` returns the type of the linked time off (``holiday_id``) when there is one.

        :rtype: hr.work.entry.type
        """
        return leave.work_entry_type_id

    # Is used to add more values, for example planning_slot_id
    def _get_more_vals_attendance_interval(self, interval):
        """Hook to add extra keys to the work entry values generated from an attendance interval.

        The result is concatenated to the base ``(key, value)`` pairs and passed to ``dict()``,
        so later pairs override earlier ones. Extensions call ``super()`` and append, e.g.
        ``hr_holidays_attendance`` adds ``('attendance_ids', attendance)`` and ``hr_payroll`` adds
        ``('category_options_ids', ...)``. A key that holds records to be unioned on merge must
        also be listed in :meth:`_get_work_entry_source_fields`.

        :param tuple interval: ``(start, stop, payload)``, tz-aware datetimes in the employee
            timezone; ``payload`` is a ``resource.calendar.attendance`` recordset (calendar
            based) or an ``hr.attendance`` record (attendance based)
        :return: list of ``(key, value)`` 2-tuples, not a dict
        :rtype: list
        """
        return []

    # Is used to add more values, for example leave_id (in hr_holidays)
    def _get_more_vals_leave_interval(self, interval, leaves):
        """Hook to add extra keys to the work entry values generated from a leave interval.

        Same contract as :meth:`_get_more_vals_attendance_interval`. ``hr_holidays`` appends
        ``('leave_ids', holiday)`` for each leave of ``leaves`` that contains ``interval`` and is
        linked to a time off.

        :param tuple interval: ``(start, stop, payload)``, tz-aware in the employee timezone
        :param list leaves: ``(start, stop, resource.calendar.leaves)`` tuples that may cover
            ``interval``
        :return: list of ``(key, value)`` 2-tuples
        :rtype: list
        """
        return []

    def _get_bypassing_work_entry_type_codes(self):
        """Return the codes of the leave types that win over public holidays.

        When a time off and a global leave (public holiday) overlap, the global leave normally
        wins. A time off whose type code is listed here wins instead (e.g. long term sick leave
        in ``l10n_be_hr_payroll``). Used by :meth:`_get_interval_leave_work_entry_type`.

        :return: list of ``hr.work.entry.type`` codes
        :rtype: list[str]
        """
        return []

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        """Return the work entry type of a leave interval.

        Base version: the type of the first leave of ``leaves`` that contains the whole
        ``interval`` (through :meth:`_get_leave_work_entry_type_dates`). ``hr_holidays``
        overrides it to arbitrate overlapping leaves: bypassing time off, then global leaves
        (public holidays), then other time off.

        :param tuple interval: ``(start, stop, payload)``, tz-aware in the employee timezone
        :param list leaves: ``(start, stop, resource.calendar.leaves)`` tuples
        :param list bypassing_codes: result of :meth:`_get_bypassing_work_entry_type_codes`
        :return: the leave's type, or ``hr_work_entry.generic_work_entry_type_leave`` if no
            leave contains the interval
        :rtype: hr.work.entry.type
        """
        # returns the work entry time related to the leave that
        # includes the whole interval.
        self.ensure_one()
        for leave in leaves:
            if interval[0] >= leave[0] and interval[1] <= leave[1] and leave[2]:
                interval_start = interval[0].astimezone(UTC).replace(tzinfo=None)
                interval_stop = interval[1].astimezone(UTC).replace(tzinfo=None)
                return self._get_leave_work_entry_type_dates(leave[2], interval_start, interval_stop, self.employee_id)
        return self.env.ref('hr_work_entry.generic_work_entry_type_leave')

    def _get_sub_leave_domain(self):
        """Return the calendar part of the domain of :meth:`_get_leave_domain`.

        Default: leaves of the versions' calendars or without calendar. ``hr_holidays`` also
        accepts the leaves linked to time off of the versions' employees, whatever the calendar.

        :rtype: odoo.fields.Domain
        """
        return Domain('calendar_id', 'in', [False] + self.resource_calendar_id.ids)

    def _get_leave_domain(self, start_dt, end_dt):
        """Return the ``resource.calendar.leaves`` domain used for work entry generation.

        Matches the leaves overlapping ``[start_dt, end_dt]`` that are global (no resource) or
        belong to the versions' employees, in the versions' companies or without company.

        :param datetime start_dt: period start, UTC (tzinfo is dropped)
        :param datetime end_dt: period end, UTC (tzinfo is dropped)
        :rtype: odoo.fields.Domain
        """
        domain = Domain([
            ('resource_id', 'in', [False] + self.employee_id.resource_id.ids),
            ('date_from', '<=', end_dt.replace(tzinfo=None)),
            ('date_to', '>=', start_dt.replace(tzinfo=None)),
            ('company_id', 'in', [False] + self.company_id.ids),
        ])
        return domain & self._get_sub_leave_domain()

    def _get_resource_calendar_leaves(self, start_dt, end_dt):
        """Return the ``resource.calendar.leaves`` to consider between ``start_dt`` and ``end_dt``.

        Override to exclude leaves from generation (``hr_payroll`` drops time off whose payslip is
        blocked/deferred).

        :param datetime start_dt: period start, UTC
        :param datetime end_dt: period end, UTC
        :rtype: resource.calendar.leaves
        """
        return self.env['resource.calendar.leaves'].search(self._get_leave_domain(start_dt, end_dt))

    def _get_attendance_intervals(self, start_dt, end_dt):
        """Return the expected working intervals of the calendar based versions of ``self``.

        Only versions with :meth:`has_static_work_entries` are computed, from their working
        schedule (``resource.resource._attendance_intervals``). A fully flexible version gets a single interval
        covering the whole period with an empty attendance payload (hence 24h per day once
        split per day).

        A module making versions non-static must override this method to still put an (empty)
        entry for their resources, as :meth:`_get_version_work_entries_values` indexes the result
        directly (see ``hr_holidays_attendance``).

        :param datetime start_dt: period start, tz-aware (asserted)
        :param datetime end_dt: period end, tz-aware (asserted)
        :return: ``{resource_id: Intervals}``, intervals being ``(start, stop,
            resource.calendar.attendance)`` in the resource timezone
        :rtype: dict
        """
        assert start_dt.tzinfo and end_dt.tzinfo, "function expects localized date"
        # {resource: intervals}
        static_versions = self.filtered(lambda version: version.has_static_work_entries())
        fully_flex_versions = static_versions.filtered(lambda version: version._is_fully_flexible())
        result = {
            version.employee_id.resource_id.id: Intervals([(start_dt, end_dt, self.env['resource.calendar.attendance'])])
            for version in fully_flex_versions
        }
        resources = (static_versions - fully_flex_versions).employee_id.resource_id
        for resource, intervals in resources._attendance_intervals(start_dt, end_dt).items():
            result[resource.id] = intervals
        return result

    def _get_interval_work_entry_type(self, interval):
        """Return the work entry type of an interval from its payload.

        The payload's ``work_entry_type_id`` (first record) if any, else the version's default
        type (:meth:`_get_default_work_entry_type_id`).

        :param tuple interval: ``(start, stop, payload)``; ``payload`` is usually a
            ``resource.calendar.attendance`` or ``resource.calendar.leaves`` recordset
        :rtype: hr.work.entry.type
        """
        self.ensure_one()
        if 'work_entry_type_id' in interval[2] and interval[2].work_entry_type_id[:1]:
            return interval[2].work_entry_type_id[:1]
        return self.env['hr.work.entry.type'].browse(self._get_default_work_entry_type_id())

    def _get_valid_leave_intervals(self, attendances, interval):
        """Filter or cut a leave interval before it is used for generation.

        Called for each leave clipped to the period. ``hr_holidays_attendance`` removes the
        parts where the employee actually worked (absence leaves) or where an attendance won
        (working time leaves).

        :param Intervals attendances: expected attendances of the version's resource
        :param tuple interval: ``(start, stop, resource.calendar.leaves)``, tz-aware in the
            employee timezone
        :return: list of ``(start, stop, payload)`` tuples to keep, possibly empty
        :rtype: list
        """
        self.ensure_one()
        return [interval]

    def _get_no_wet_or_wet_match(self, leave, leave_entry_type):
        """Tell whether ``leave`` is a source of a leave work entry of type ``leave_entry_type``.

        True if the calendar leave has no type or the same type. Only the matching leaves are
        given to :meth:`_get_more_vals_leave_interval`, so a mismatch means no ``leave_ids`` on the
        generated values.

        :param tuple leave: ``(start, stop, resource.calendar.leaves)``
        :param leave_entry_type: the ``hr.work.entry.type`` chosen for the interval
        :rtype: bool
        """
        return not leave[2].work_entry_type_id or leave[2].work_entry_type_id.id == leave_entry_type.id

    # Meant for behavior override
    def _get_real_attendance_work_entry_vals(self, intervals):
        """Convert attendance intervals into raw work entry values.

        Meant for behavior override.

        :param intervals: iterable of ``(start, stop, payload)``, tz-aware
        :return: one dict per interval with ``date_start`` and ``date_stop`` (naive UTC),
            ``work_entry_type_id`` (:meth:`_get_interval_work_entry_type`), ``employee_id``,
            ``version_id``, ``company_id`` (all recordsets), plus the pairs of
            :meth:`_get_more_vals_attendance_interval`
        :rtype: list[dict]
        """
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
        """Compute the raw work entry values of the versions of ``self`` over a period.

        Core of the generation, batched over versions. For each version:

        - expected attendances: :meth:`_get_attendance_intervals`;
        - leaves: :meth:`_get_resource_calendar_leaves`, clipped to the period and filtered by
          :meth:`_get_valid_leave_intervals`, split on the calendar leave's ``count_as``:
          ``absence`` leaves replace the expected attendances they overlap, ``working_time``
          leaves (e.g. home working) produce worked leave entries;
        - real attendances = attendances minus both kinds of leaves
          (:meth:`_get_real_attendances`); the leave intervals actually generated depend on the
          calendar type (fully flexible, flexible, static, or attendance based).

        Override it to add or replace values for a localization (``l10n_fr_hr_holidays``,
        ``l10n_uz_hr_payroll``) or for a new source of time (``hr_holidays_attendance`` adds the
        ``hr.attendance`` based values). Values must be completed by
        :meth:`_generate_work_entries_postprocess` before use.

        :param datetime date_start: period start; naive datetimes are considered UTC
        :param datetime date_stop: period end; naive datetimes are considered UTC
        :return: list of dicts with ``date_start`` and ``date_stop`` (naive UTC),
            ``work_entry_type_id``, ``employee_id``, ``version_id``, ``company_id`` (recordsets)
            and the extra keys of the ``_get_more_vals_*`` hooks. Alternatively, a value may
            carry ``date`` and ``duration`` directly.
        :rtype: list[dict]
        """
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
            if version._is_fully_flexible():
                real_leaves = leaves
            elif version._is_flexible():
                # Flexible hours case
                # For multi day leaves, we want them to occupy the virtual working schedule 12 AM to average working days
                # For one day leaves, we want them to occupy exactly the time it was taken, for a time off in days
                # this will mean the virtual schedule and for time off in hours the chosen hours
                one_day_leaves = Intervals([l for l in leaves if l[0].astimezone(tz).date() == l[1].astimezone(tz).date()], keep_distinct=True)
                multi_day_leaves = leaves - one_day_leaves
                static_attendances = employee.resource_id._attendance_intervals(start_dt, end_dt)[employee.resource_id]
                real_leaves = (static_attendances & multi_day_leaves) | one_day_leaves
            elif version.has_static_work_entries() or not leaves:
                real_leaves = version._get_real_leaves_static(leaves, expected_attendances)
            else:
                static_attendances = employee.resource_id._attendance_intervals(start_dt, end_dt)[employee.resource_id]
                real_leaves = version._get_real_leaves_static_attendance(leaves, static_attendances)

            real_worked_leaves = version._get_real_worked_leaves(worked_leaves, real_leaves)
            real_attendances = version._get_real_attendances(expected_attendances, leaves, worked_leaves)

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
                    interval_leaves = [leave for leave in leaves if version._get_no_wet_or_wet_match(leave, leave_entry_type)]
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
        """Return the attendance intervals that produce worked time entries.

        Default: expected attendances minus absence and worked leaves.
        ``hr_holidays_attendance`` also removes the days where the employee has real
        ``hr.attendance`` records.

        :param Intervals attendances: expected attendances
        :param Intervals leaves: absence leaves
        :param Intervals worked_leaves: working time leaves
        :rtype: Intervals
        """
        return attendances - leaves - worked_leaves

    def _get_real_leaves_static(self, leaves, expected_attendances):
        """Return the absence intervals to generate for a static (calendar based) version.

        Default: the parts of ``leaves`` that overlap the expected attendances, i.e. a leave
        only produces entries where the employee was supposed to work.

        :rtype: Intervals
        """
        return expected_attendances & leaves

    def _get_real_leaves_static_attendance(self, leaves, static_attendances):
        """Return the absence intervals to generate for a non-static (attendance based) version.

        The expected attendances are empty for such a version, so leaves are intersected with the
        intervals of its working schedule instead.

        :rtype: Intervals
        """
        return static_attendances & leaves

    def _get_real_worked_leaves(self, worked_leaves, real_leaves):
        """Return the working time leave intervals to generate.

        Default: worked leaves minus the absence intervals (an absence wins over a working time
        leave).

        :rtype: Intervals
        """
        return worked_leaves - real_leaves

    def _get_work_entries_values(self, date_start, date_stop):
        """Return the raw work entry values of the versions of ``self`` between two dates.

        Thin wrapper on :meth:`_get_version_work_entries_values`. With datetimes, the versions are
        processed in one batch. With plain dates, the period goes from the start of
        ``date_start`` to the end of ``date_stop`` in each version's timezone.

        :param date_start: period start, ``datetime`` (naive is considered UTC) or ``date``
        :param date_stop: period end, ``datetime`` (naive is considered UTC) or ``date``
            (included)
        :return: raw values, see :meth:`_get_version_work_entries_values`
        :rtype: list[dict]
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
                    datetime.combine(date_start, time.min, tzinfo=tz),
                    # the end excluded, at the start of the day after date_stop
                    datetime.combine(date_stop + timedelta(days=1), time.min, tzinfo=tz))

        return version_vals

    def has_static_work_entries(self):
        """Tell whether the work entries of this version come from its working schedule.

        ``True`` (default): worked time is generated from the calendar attendances.
        ``False``: worked time comes from another source; ``hr_holidays_attendance`` returns
        ``not attendance_based``, worked time then coming from validated ``hr.attendance``
        records. See :meth:`_get_attendance_intervals` for what an override must also do.

        :rtype: bool
        """
        # True means this is calendar based, False it is attendance based.
        self.ensure_one()
        return True

    def generate_work_entries(self, date_start, date_stop):
        """Return the final work entry values of the versions of ``self`` between two dates.

        Main entry point, used by payroll (``hr.payslip._compute_worked_days_line_ids``). Nothing
        is stored: the values are computed on the fly. The days are localized in the version's
        timezone, then the versions are processed per (company, timezone) as superuser with
        :meth:`_generate_work_entries`, which clips the period to each version's validity.

        :param date date_start: first day, included (``datetime`` is refused)
        :param date date_stop: last day, included (``datetime`` is refused)
        :return: list of dicts, at most one per (``date``, type, employee, version, company)
            and extra merge key parts (see :meth:`_get_work_entry_merge_key`), with keys:

            - ``date``: local day (``datetime.date``) in the version's timezone
            - ``duration``: hours (float, never zero)
            - ``work_entry_type_id``, ``employee_id``, ``version_id``, ``company_id``: records
            - optional keys added by extensions: ``leave_ids`` (``hr.leave``),
              ``attendance_ids`` (``hr.attendance``), ``category_options_ids``,
              ``trimmed_duration`` (``hr_payroll``)...
        :rtype: list[dict]
        """
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
        """Compute and post-process the work entry values between two datetimes.

        Clips the period to each version's ``[date_start, date_end]`` (whole local days), groups
        versions sharing the same clipped period, calls :meth:`_get_work_entries_values` and
        finally :meth:`_generate_work_entries_postprocess`.

        :param datetime date_start: period start, naive UTC, already localized by the caller
        :param datetime date_stop: period end, naive UTC
        :return: final values, see :meth:`generate_work_entries`
        :rtype: list[dict]
        """
        # Generate work entries between 2 dates (datetime.datetime)
        # This method considers that the dates are correctly localized
        # based on the target timezone
        assert isinstance(date_start, datetime)
        assert isinstance(date_stop, datetime)
        self = self.with_context(tracking_disable=True)  # noqa: PLW0642
        vals_list = []

        intervals_to_generate = defaultdict(lambda: self.env['hr.version'])

        for version_tz, versions in self.grouped(lambda v: v._get_tz()).items():
            tz = ZoneInfo(version_tz) if version_tz else UTC
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
        """Return the keys whose values are unioned when work entry values are merged.

        Used by :meth:`_generate_work_entries_postprocess`: when two values share the same merge
        key, these recordset keys are combined with ``|``. Extensions add their source keys
        (``leave_ids`` in ``hr_holidays``, ``attendance_ids`` in ``hr_holidays_attendance``).

        :return: list of keys to aggregate
        :rtype: list[str]
        """
        return []

    def _enrich_work_entry_val(self, val):
        """Hook called on each value once ``date`` and ``duration`` are set, before merging.

        Modify ``val`` in place. At this point ``leave_ids`` (if any) is still a single record,
        so field access is safe. ``hr_payroll`` sets ``trimmed_duration``, which is summed when
        values are merged. Default: no-op.

        :param dict val: one work entry value
        """

    @api.model
    def _get_work_entry_merge_key(self, vals):
        """Return the key identifying the work entry values to merge into one.

        Values with the same key are merged by summing ``duration``. Default key:
        ``(date, work_entry_type_id, employee_id, version_id, company_id)``. Extend the tuple
        to keep values apart (``hr_payroll`` adds ``category_options_ids``).

        :param dict vals: one work entry value, with ``date`` set
        :rtype: tuple
        """
        return (
            vals['date'],
            vals.get('work_entry_type_id', False),
            vals['employee_id'],
            vals['version_id'],
            vals.get('company_id', False),
        )

    @api.model
    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        """Tell whether the duration of a value is computed from the working schedule.

        ``True``: ``duration`` is the number of hours the version's calendar plans in the value's
        span (``_get_work_days_data_batch`` with ``compute_leaves=False``), so a time off counts
        the planned hours. ``False``: ``duration`` is the real length of the span.
        Default: ``True`` for absence types. ``hr_holidays`` also returns ``True`` for time off
        types not requested in hours (but ``False`` for time rule outputs);
        ``hr_holidays_attendance`` returns ``False`` for attendance values and fully flexible
        versions. Overrides must not rely on ``vals`` keys other than the raw ones.

        :param dict vals: raw value (``date_start``/``date_stop`` still set)
        :rtype: bool
        """
        if 'work_entry_type_id' not in vals:
            return False
        work_entry_type = vals['work_entry_type_id']
        return work_entry_type.count_as == 'absence'

    @api.model
    def _get_work_days_data_by_period(self, calendar, employees_by_period):
        """Return the planned time of the employees on several periods, in a calendar.

        Same result as ``employees._get_work_days_data_batch(date_start, date_stop,
        compute_leaves=False, calendar=calendar)`` for each period, but the attendance intervals
        are computed once for all the periods (the post-processing has one period per day of
        absence), then clipped to each of them. Only when the intervals do not depend on the
        period: neither the calendar nor any calendar of the employees is flexible (see
        ``resource.calendar._attendance_intervals_batch``); otherwise each period is computed
        on its own.

        :param calendar: ``resource.calendar``
        :param dict employees_by_period: ``{(date_start, date_stop): hr.employee}``, datetimes
            in UTC (naive means UTC)
        :return: ``{(date_start, date_stop): {employee_id: {'days': float, 'hours': float}}}``
        :rtype: dict
        """
        all_employees = self.env['hr.employee'].union(employees_by_period.values())
        employee_calendars = (
            calendar
            | all_employees.resource_calendar_id
            | all_employees.sudo().with_context(active_test=False).version_ids.resource_calendar_id
        )
        if (len(employees_by_period) == 1 or not calendar
                or any(employee_calendar._is_flexible() for employee_calendar in employee_calendars)):
            return {
                (date_start, date_stop): employees._get_work_days_data_batch(
                    date_start, date_stop, compute_leaves=False, calendar=calendar)
                for (date_start, date_stop), employees in employees_by_period.items()
            }

        result = defaultdict(dict)
        start = min(localized(date_start) for date_start, _date_stop in employees_by_period)
        stop = max(localized(date_stop) for _date_start, date_stop in employees_by_period)
        for tz, tz_resources in all_employees.resource_id._get_resources_per_tz().items():
            # the intervals of the calendar itself, those of any of its non flexible resources
            intervals = list(calendar._attendance_intervals_batch(
                start, stop, {tz: self.env['resource.resource']})[False])
            interval_stops = [interval_stop for _interval_start, interval_stop, _records in intervals]
            tz_resource_ids = set(tz_resources.ids)
            for (date_start, date_stop), employees in employees_by_period.items():
                tz_employees = employees.filtered(lambda employee: employee.resource_id.id in tz_resource_ids)
                if not tz_employees:
                    continue
                period_start = localized(date_start).astimezone(tz)
                period_stop = localized(date_stop).astimezone(tz)
                # the intervals overlapping the period, clipped as the period alone would
                period_intervals = []
                index = bisect_right(interval_stops, period_start)
                while index < len(intervals) and intervals[index][0] < period_stop:
                    interval_start, interval_stop, records = intervals[index]
                    period_intervals.append((max(period_start, interval_start), min(period_stop, interval_stop), records))
                    index += 1
                data = calendar._get_attendance_intervals_days_data(Intervals(period_intervals, keep_distinct=True))
                for employee in tz_employees:
                    result[date_start, date_stop][employee.id] = dict(data)
        return result

    @api.model
    def _generate_work_entries_postprocess(self, vals_list):
        """Turn raw work entry values into final ``date``/``duration`` values.

        Steps:

        1. values without ``date_start``/``date_stop`` must already have ``date`` and
           ``duration`` (``UserError`` otherwise) and are kept as is;
        2. the others are split at each local midnight (timezone of ``version_id``);
        3. ``date`` is the local day of the start; ``duration`` is kept if given, otherwise
           computed from the calendar or from the span, see
           :meth:`_generate_work_entries_postprocess_adapt_to_calendar`; ``date_start`` and
           ``date_stop`` are removed, then :meth:`_enrich_work_entry_val` is called;
        4. values with a zero duration (3 digits) are dropped, the others are merged by
           :meth:`_get_work_entry_merge_key`, summing ``duration`` and ``trimmed_duration`` and
           unioning the :meth:`_get_work_entry_source_fields` keys.

        A raw value providing ``duration`` should also provide ``date``, and should not cross
        local midnight (each split part would keep the full duration).

        :param list vals_list: raw values, see :meth:`_get_version_work_entries_values`
        :return: final values, see :meth:`generate_work_entries`
        :rtype: list[dict]
        :raise UserError: when a version has no timezone or a value has neither dates nor
            ``date`` and ``duration``
        """
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
            employee = version.employee_id
            mapped_periods[date_start, date_stop][calendar] |= employee

        # {(date_start, date_stop): {calendar: {'hours': foo}}}
        mapped_version_data = defaultdict(lambda: defaultdict(lambda: {'hours': 0.0}))
        employees_by_calendar_period = defaultdict(dict)
        for period, employees_by_calendar in mapped_periods.items():
            for calendar, employees in employees_by_calendar.items():
                employees_by_calendar_period[calendar][period] = employees
        for calendar, employees_by_period in employees_by_calendar_period.items():
            for period, data in self._get_work_days_data_by_period(calendar, employees_by_period).items():
                mapped_version_data[period][calendar] = data

        for vals in vals_list:
            if 'duration' not in vals:
                date_start = vals['date_start']
                date_stop = vals['date_stop']
                version = vals['version_id']
                calendar = version.resource_calendar_id
                employee = version.employee_id
                tz = _get_tz(version)
                vals['date'] = date_start.astimezone(tz).date()
                vals['duration'] = mapped_version_data[date_start, date_stop][calendar][employee.id]['hours']
            vals.pop('date_start', False)
            vals.pop('date_stop', False)
            self._enrich_work_entry_val(vals)

        # Now merge similar work entries on the same day
        merged_vals = {}
        for vals in vals_list:
            if float_is_zero(vals['duration'], 3):
                continue
            key = self._get_work_entry_merge_key(vals)
            if key in merged_vals:
                merged_vals[key]['duration'] += vals.get('duration', 0.0)
                source_fields = self._get_work_entry_source_fields()
                for field in source_fields:
                    if field in merged_vals[key] and field in vals:
                        merged_vals[key][field] |= vals[field]
                # sum any float sub-totals tagged by _enrich_work_entry_val
                if 'trimmed_duration' in vals:
                    merged_vals[key]['trimmed_duration'] = (
                        merged_vals[key].get('trimmed_duration', 0.0) + vals['trimmed_duration']
                    )
            else:
                merged_vals[key] = vals.copy()
        return list(merged_vals.values())
