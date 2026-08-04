# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from functools import partial
from itertools import chain
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import float_compare
from odoo.tools.date_utils import float_to_time, localized, time_to_float, to_timezone
from odoo.tools.float_utils import float_round
from odoo.tools.intervals import Intervals

_logger = logging.getLogger(__name__)


class ResourceCalendar(models.Model):
    """ Working schedule ("Working Time") of resources. It holds:

    - ``attendance_ids``: the ``resource.calendar.attendance`` lines defining when
      work is expected (per weekday for ``fixed`` calendars, per date, optionally
      recurring, for ``variable`` ones, none for ``undefined`` / flexible ones);
    - ``leave_ids``: the ``resource.calendar.leaves`` linked to this calendar. A leave
      without ``resource_id`` is global (public holiday for every resource of the
      calendar), otherwise it only applies to that resource.

    The computation API works on :class:`~odoo.tools.intervals.Intervals` of
    ``(start, stop, records)`` triples, where ``start``/``stop`` are timezone-aware
    datetimes and ``records`` is the attendance or leave recordset that produced the
    interval. Batch methods return a dict ``{resource_id: Intervals}`` in which the
    key ``False`` holds the calendar-level result (no specific resource). """
    _name = 'resource.calendar'
    _description = "Resource Working Time"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not res.get('name') and res.get('company_id'):
            res['name'] = self.env._('Working Hours of %s', self.env['res.company'].browse(res['company_id']).name)
        return res

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        for calendar, vals in zip(self, vals_list):
            # the rates of a fixed calendar are computed from its attendances, those of the other
            # calendars are set by the user: they are kept on the copy
            if vals.get('calendar_type', calendar.calendar_type) != 'fixed':
                vals.setdefault('days_per_week', calendar.days_per_week)
                vals.setdefault('hours_per_week', calendar.hours_per_week)
        return vals_list

    name = fields.Char(required=True)
    active = fields.Boolean("Active", default=True,
                            help="If the active field is set to false, it will allow you to hide the Working Time without removing it.")
    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Working Time', precompute=True,
        compute='_compute_attendance_ids', store=True, readonly=False, copy=True)
    company_id = fields.Many2one(
        'res.company', 'Company', domain=lambda self: [('id', 'in', self.env.companies.ids)],
        default=lambda self: self.env.company, index='btree_not_null')
    country_id = fields.Many2one(related='company_id.country_id')
    country_code = fields.Char(related='country_id.code', depends=['country_id'])
    leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Time Off')
    full_time_required_hours = fields.Float(
        string="Full Time Equivalent",
        compute="_compute_full_time_required_hours", store=True, readonly=False,
        help="Number of hours to work on the company schedule to be considered as fulltime.")
    global_leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Global Time Off',
        compute='_compute_global_leave_ids', store=True, readonly=False,
        domain=[('resource_id', '=', False)],
    )
    days_per_week = fields.Float("Days per Week", compute="_compute_days_per_week", store=True, digits=(10, 5), readonly=False, copy=False)
    hours_per_day = fields.Float("Average Hour per Day", store=True, compute="_compute_hours_per_day", digits=(10, 5), readonly=False,
        help="Average hours per day a resource is supposed to work with this calendar.", copy=False)
    hours_per_week = fields.Float(
        string="Hours per Week",
        compute="_compute_hours_per_week", store=True, digits=(10, 5), readonly=False, copy=False)
    is_fulltime = fields.Boolean(compute='_compute_is_fulltime', string="Is Full Time")
    work_resources_count = fields.Integer("Work Resources count", compute='_compute_work_resources_count')
    work_time_rate = fields.Float(string='Work Time Rate', compute='_compute_work_time_rate', store=True,
        help='Work time rate versus full time working schedule, should be between 0 and 100 %.')
    calendar_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('variable', 'Variable'),
        ('undefined', 'Undefined')],
        string='Calendar Type', default='fixed', required=True,
        help="""
    - Fixed: a weekly attendance pattern that repeats identically every week.
    - Variable: attendances set on specific dates rather than a repeating weekly pattern, such as a one-off schedule or a multi-week rotation.
    - Undefined: no predefined slots at all. The resource can work whenever it wants, optionally up to an hours target.
        """)
    reference_calendar_id = fields.Many2one(
        'resource.calendar',
        string="Reference Calendar",
        index='btree_not_null',
        check_company=True,
        help="Reference working hours used to compute the full-time equivalent.")

    def _is_flexible(self):
        """ Return whether this calendar is flexible, i.e. of type ``undefined``: it has no
        attendance lines and the resource may work whenever it wants, optionally up to the
        ``hours_per_week`` / ``hours_per_day`` targets (see :meth:`_is_fully_flexible`). """
        self.ensure_one()
        return self.calendar_type == 'undefined'

    def _is_fully_flexible(self):
        """ Return whether this calendar is flexible (see :meth:`_is_flexible`) and has no
        hours target either (``hours_per_week`` and ``hours_per_day`` both zero). A fully
        flexible resource is considered working during the whole requested period. """
        self.ensure_one()
        return self._is_flexible() and not self.hours_per_week and not self.hours_per_day

    def _get_attendances_to_unlink(self, next_calendar_type=None):
        """ Return the attendances that do not fit the calendar's ``calendar_type`` (or
        ``next_calendar_type`` when given), and must be dropped:

        - ``fixed``: attendances with a date (fixed calendars use undated weekly lines);
        - ``undefined``: every attendance (flexible calendars have no predefined slots);
        - ``variable``: attendances without a date (variable calendars use dated lines).

        Called after every ``create``/``write`` of calendars.

        :rtype: ``resource.calendar.attendance`` recordset
        """
        def to_unlink(attendance):
            calendar_type = next_calendar_type or attendance.calendar_id.calendar_type
            if calendar_type == 'undefined':
                return True
            return bool(attendance.date) if calendar_type == 'fixed' else not attendance.date
        return self.attendance_ids.filtered(to_unlink)

    def _convert_single_occurrence_recurrencies(self):
        """Convert recurrent attendances with only one visible occurrence into ad-hoc attendances."""
        def _has_single_remaining_occurrence(att):
            if not att.recurrency or not att.date or att.recurrency_end_type == 'forever':
                return False
            excluded = set(att.recurrency_excluded_occurences or [])
            delta = timedelta(**{att.recurrency_type: att.recurrency_interval})
            current = att.date + delta
            while current <= att.recurrency_until:
                if fields.Date.to_string(current) not in excluded:
                    return False
                current += delta
            return True

        single_occurrence = self.attendance_ids.filtered(_has_single_remaining_occurrence)
        single_occurrence.write({'recurrency': False, 'recurrency_excluded_occurences': False})

    def _clean_excluded_occurrences(self):
        """Remove stale or duplicate entries from ``recurrency_excluded_occurences``.

        Removes dates before the attendance start, dates past ``recurrency_until``,
        dates that don't fall on a valid recurrency occurrence, and duplicates —
        in a single pass per attendance.
        """
        for att in self.attendance_ids.filtered(lambda a: a.recurrency and a.recurrency_excluded_occurences and a.date):
            date_str = fields.Date.to_string(att.date)
            until_str = fields.Date.to_string(att.recurrency_until) if att.recurrency_end_type != 'forever' else None
            seen = set()
            cleaned = []
            for d in att.recurrency_excluded_occurences:
                if d < date_str or (until_str and d > until_str) or d in seen:
                    continue
                diff_days = (fields.Date.from_string(d) - att.date).days
                if att.recurrency_type == 'days' and diff_days % att.recurrency_interval:
                    continue
                if att.recurrency_type == 'weeks' and (diff_days % 7 or (diff_days // 7) % att.recurrency_interval):
                    continue
                seen.add(d)
                cleaned.append(d)
            if cleaned != att.recurrency_excluded_occurences:
                att.recurrency_excluded_occurences = cleaned

    def _calendar_clean_up(self):
        """Clean up the attendances of the calendars in ``self`` (all calendars when
        ``self`` is empty): drop lines not matching the calendar type, clean excluded
        occurrences and turn recurrences with a single remaining occurrence into
        one-off attendances."""
        calendars = self or self.search([])
        calendars._get_attendances_to_unlink().unlink()
        calendars._clean_excluded_occurrences()
        calendars._convert_single_occurrence_recurrencies()

    # --------------------------------------------------
    # Compute Methods
    # --------------------------------------------------

    @api.depends('reference_calendar_id', 'reference_calendar_id.hours_per_week', 'hours_per_week', 'company_id.resource_calendar_id.hours_per_week')
    def _compute_full_time_required_hours(self):
        for calendar in self:
            if calendar.reference_calendar_id:
                calendar.full_time_required_hours = calendar.reference_calendar_id.hours_per_week
            elif calendar.company_id.resource_calendar_id:
                calendar.full_time_required_hours = calendar.company_id.resource_calendar_id.hours_per_week
            else:
                calendar.full_time_required_hours = calendar.hours_per_week

    @api.depends('company_id', 'calendar_type')
    def _compute_attendance_ids(self):
        for calendar in self:
            calendar_changed = calendar._origin and calendar._origin.company_id != calendar.company_id
            if (not calendar.id or calendar_changed) and calendar.calendar_type == "fixed" and not calendar.attendance_ids:
                calendar.attendance_ids = calendar._get_default_attendance_ids(calendar.company_id)

    @api.depends('company_id')
    def _compute_global_leave_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or c._origin.company_id != c.company_id):
            calendar.update({
                'global_leave_ids': [(5, 0, 0)] + [
                    (0, 0, leave._copy_leave_vals()) for leave in calendar.company_id.resource_calendar_id.global_leave_ids],
            })

    @api.depends('attendance_ids.dayofweek', 'calendar_type')
    def _compute_days_per_week(self):
        for calendar in self:
            # variable/undefined calendars don't have a reliable attendance pattern to derive
            # this from (undefined calendars have none at all); the user sets it directly instead.
            if calendar.calendar_type != 'fixed':
                continue
            attendances = calendar.attendance_ids.filtered(lambda a: a._is_work_period())
            calendar.days_per_week = len(set(attendances.mapped('dayofweek')))

    @api.depends('days_per_week', 'hours_per_week')
    def _compute_hours_per_day(self):
        for calendar in self:
            calendar.hours_per_day = calendar.hours_per_week / calendar.days_per_week if calendar.days_per_week else 0

    @api.depends('attendance_ids.duration_hours', 'calendar_type')
    def _compute_hours_per_week(self):
        """ Compute the average hours per week """
        for calendar in self:
            # see _compute_days_per_week: variable/undefined calendars are set directly by the user
            if calendar.calendar_type != 'fixed':
                continue
            attendances = calendar.attendance_ids.filtered(lambda a: a._is_work_period())
            calendar.hours_per_week = sum(attendances.mapped('duration_hours'))

    def _compute_work_resources_count(self):
        resources_per_calendar = dict(self.env['resource.resource']._read_group(
            domain=[('calendar_id', 'in', self.ids)],
            groupby=['calendar_id'],
            aggregates=['__count']))
        for calendar in self:
            calendar.work_resources_count = resources_per_calendar.get(calendar, 0)

    @api.constrains('hours_per_week', 'hours_per_day')
    def _verify_hours(self):
        for calendar in self:
            # fixed calendars derive these from their attendance lines, always valid by construction
            if calendar.calendar_type == 'fixed':
                continue
            if calendar.hours_per_week < 0 or calendar.hours_per_week > 168:
                raise ValidationError(self.env._("Hours per week must be between 0 and 168."))
            if calendar.hours_per_day < 0 or calendar.hours_per_day > 24:
                raise ValidationError(self.env._("Average hours per day must be between 0 and 24."))

    @api.depends('hours_per_week', 'full_time_required_hours')
    def _compute_is_fulltime(self):
        for calendar in self:
            calendar.is_fulltime = float_compare(calendar.full_time_required_hours, calendar.hours_per_week, 3) == 0

    @api.depends('hours_per_week', 'full_time_required_hours')
    def _compute_work_time_rate(self):
        for calendar in self:
            if calendar.full_time_required_hours:
                calendar.work_time_rate = calendar.hours_per_week / calendar.full_time_required_hours
            else:
                calendar.work_time_rate = 1.0

    def is_calendar_referenced(self):
        """ Return whether any stored many2one field of a non-abstract model (other than
        the ``resource.calendar*`` models) points to this calendar. Searches as superuser. """
        self.ensure_one()
        relations = self.env['ir.model.fields'].sudo().search([
            ('ttype', '=', 'many2one'),
            ('store', '=', True),
            ('model', 'not ilike', 'resource.calendar'),
            ('model_id.abstract', '=', False),
            ('relation', '=', "resource.calendar")
        ])
        for field in relations:
            count = self.env[field.model].sudo().search_count([(field.name, '=', self.id)], limit=1)
            if count:
                return True
        return False

    # --------------------------------------------------
    # Overrides
    # --------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        calendars = super().create(vals_list)
        calendars._get_attendances_to_unlink().unlink()
        return calendars

    def write(self, vals):
        res = super().write(vals)
        self._get_attendances_to_unlink().unlink()
        return res

    # --------------------------------------------------
    # Computation API
    # --------------------------------------------------

    def _attendance_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None):
        """ Return the theoretical work intervals generated by the attendance lines of this
        calendar between ``start_dt`` and ``end_dt``, leaves NOT deducted.

        Each interval is clipped to ``[start_dt, end_dt]``, expressed in the timezone of the
        resource (attendance hours are local times) and carries its single attendance record
        as payload (``keep_distinct=True``: two adjacent attendances stay two intervals).
        Duration-based attendances (no ``hour_from``/``hour_to``) are placed contiguously,
        centered on 12:00.

        Flexible resources get synthetic intervals instead, based on the calendar returned
        by ``resource._get_calendar_data_at`` (the resource's own calendar, or the employee's
        version calendar with ``hr``), not on ``self``:

        - fully flexible: a single interval covering the whole period;
        - flexible with hours targets: one interval per day of at most ``hours_per_day``,
          centered on 12:00, until ``hours_per_week`` is reached in each 7-day block counted
          from ``start_dt`` (not calendar weeks).

        Their payload is a new (unsaved) attendance holding only ``duration_hours``.

        ``self`` holds at most one calendar. It may be empty when ``resources_per_tz`` is
        given, but then only flexible resources get intervals.

        :param datetime start_dt: timezone-aware start of the period
        :param datetime end_dt: timezone-aware end of the period
        :param dict resources_per_tz: ``{ZoneInfo: resource.resource recordset}``, as returned
            by ``resources._get_resources_per_tz()``. Defaults to no resource, in the timezone
            of ``start_dt``.
        :param domain: optional domain on ``resource.calendar.attendance`` restricting the
            attendances used. When given, the flexible handling above is skipped.
        :return: ``{resource_id: Intervals}`` for every resource of ``resources_per_tz``, plus
            the key ``False`` (calendar-level, no resource) when ``self`` is set. With several
            timezones, the ``False`` entry is expressed in the last timezone of
            ``resources_per_tz``.
        :rtype: dict
        """
        _logger.warning("The method _attendance_intervals_batch is deprecated. Use TODO BEDO NEW NAME instead.")
        assert start_dt.tzinfo and end_dt.tzinfo
        if self:
            self.ensure_one()
        elif not resources_per_tz:
            raise UserError(self.env._("You cannot compute the intervals without a calendar on no resource."))

        if not resources_per_tz:
            resources_per_tz = {start_dt.tzinfo: self.env['resource.resource']}

        start = start_dt.astimezone(UTC)
        end = end_dt.astimezone(UTC)
        bounds_per_tz = {
            tz: (start_dt.astimezone(tz), end_dt.astimezone(tz))
            for tz in resources_per_tz
        }
        # Use the outer bounds from the requested timezones
        for low, high in bounds_per_tz.values():
            start = min(start, low.replace(tzinfo=UTC))
            end = max(end, high.replace(tzinfo=UTC))

        domain = Domain(domain or Domain.TRUE)
        if self:
            attendances_per_day = self._get_attendances_by_date(start.date(), end.date(), domain | Domain('duration_based', '=', True))
        else:
            attendances_per_day = defaultdict(lambda: self.env['resource.calendar.attendance'])

        # Generate once with utc as timezone
        base_result = []
        for day, all_attendances in attendances_per_day.items():
            # If all attendance lines are duration based, compute correct intervals
            all_duration_based_attendances = all_attendances.filtered('duration_based')
            attendances = all_attendances.filtered(domain)
            if all(att.duration_based for att in attendances):
                total_hours = sum(all_duration_based_attendances.mapped('duration_hours'))
                hours_per_attendance = {}
                current_hour_from = 12 - total_hours / 2
                for att in all_duration_based_attendances:
                    hours_per_attendance[att] = (current_hour_from, current_hour_from + att.duration_hours)
                    current_hour_from += att.duration_hours
                for att in attendances:
                    hour_from, hour_to = hours_per_attendance[att]
                    day_from = datetime.combine(day, float_to_time(hour_from))
                    day_to = datetime.combine(day, float_to_time(hour_to))
                    base_result.append((day_from, day_to, att))
                continue

            for attendance in attendances:
                if attendance.duration_based:
                    day_from = datetime.combine(day, float_to_time(12 - attendance.duration_hours / 2))
                    day_to = datetime.combine(day, float_to_time(12 + attendance.duration_hours / 2))
                    base_result.append((day_from, day_to, attendance))
                else:
                    day_from = datetime.combine(day, float_to_time(attendance.hour_from))
                    day_to = datetime.combine(day, float_to_time(attendance.hour_to))
                    base_result.append((day_from, day_to, attendance))

        # Copy the result localized once per necessary timezone
        # Strictly speaking comparing start_dt < time or start_dt.astimezone(tz) < time
        # should always yield the same result. however while working with dates it is easier
        # if all dates have the same format
        result_per_tz = {
            tz: [(max(bounds_per_tz[tz][0], val[0].replace(tzinfo=tz)),
                min(bounds_per_tz[tz][1], val[1].replace(tzinfo=tz)),
                val[2])
                    for val in base_result]
            for tz in resources_per_tz
        }
        result_per_resource_id = dict()
        for tz, tz_resources in resources_per_tz.items():
            res = result_per_tz[tz]
            calendar_data_by_resource = tz_resources._get_calendar_data_at(start_dt, tz)

            res_intervals = Intervals(res, keep_distinct=True)
            start_datetime = start_dt.astimezone(tz)
            end_datetime = end_dt.astimezone(tz)

            for resource in chain(tz_resources, (self.env['resource.resource'],) if self else ()):
                if resource:
                    calendar_data = calendar_data_by_resource.get(resource, {})
                else:
                    calendar_data = {'resource_calendar_id': self, 'hours_per_week': self.hours_per_week, 'hours_per_day': self.hours_per_day}
                # resource_calendar_id is always set: it's required on both resource.resource and
                # hr.version nowadays, and the fake/falsy resource above is given self's own calendar.
                calendar = calendar_data.get('resource_calendar_id', self.env['resource.calendar'])
                hours_per_week = calendar_data.get('hours_per_week')
                hours_per_day = calendar_data.get('hours_per_day')
                calendar_is_flexible = calendar._is_flexible()
                is_fully_flexible = calendar_is_flexible and not hours_per_week and not hours_per_day
                is_flexible = calendar_is_flexible and not is_fully_flexible
                if not domain and is_fully_flexible:
                    # A domain is only provided in extensions of `_work_intervals_batch` so when a domain is present,
                    # we should use the standard attendance intervals rather than the flexible employee special handling.
                    # This prevents a scenario where `_work_intervals_batch` calls this method twice and returns the same
                    # value, causing the them to cancel out.
                    #
                    # If the resource is fully flexible, return the whole period from start_dt to end_dt with a dummy attendance
                    hours = (end_dt - start_dt).total_seconds() / 3600
                    dummy_attendance = self.env['resource.calendar.attendance'].new({
                        'duration_hours': hours,
                    })
                    result_per_resource_id[resource.id] = Intervals([(start_datetime, end_datetime, dummy_attendance)], keep_distinct=True)
                elif not domain and is_flexible:
                    # For flexible Calendars, we create intervals to fill in the weekly intervals with the average daily hours
                    # until the full time required hours are met. This gives us the most correct approximation when looking at a daily
                    # and weekly range for time offs and overtime calculations and work entry generation
                    start_date = start_datetime
                    end_datetime_adjusted = end_datetime - relativedelta(seconds=1)
                    end_date = end_datetime_adjusted

                    full_time_required_hours = hours_per_week
                    max_hours_per_day = hours_per_day

                    intervals = []
                    current_start_day = start_date

                    while current_start_day <= end_date:
                        current_end_of_week = current_start_day + timedelta(days=6)

                        week_start = max(current_start_day, start_date)
                        week_end = min(current_end_of_week, end_date)

                        if current_start_day < start_date:
                            prior_days = (start_date - current_start_day).days
                            prior_hours = min(full_time_required_hours, max_hours_per_day * prior_days)
                        else:
                            prior_hours = 0

                        remaining_hours = max(0, full_time_required_hours - prior_hours)
                        remaining_hours = min(remaining_hours, (end_dt - start_dt).total_seconds() / 3600)

                        current_day = week_start
                        while current_day <= week_end:
                            if remaining_hours > 0:
                                day_start = datetime.combine(current_day, time.min, tzinfo=tz)
                                day_end = datetime.combine(current_day, time.max, tzinfo=tz)
                                day_period_start = max(start_datetime, day_start)
                                day_period_end = min(end_datetime, day_end)
                                allocate_hours = min(max_hours_per_day, remaining_hours, (day_period_end - day_period_start).total_seconds() / 3600)
                                remaining_hours -= allocate_hours

                                # Create interval centered at 12:00 PM
                                midpoint = datetime.combine(current_day, time(12, 0), tzinfo=tz)
                                start_time = midpoint - timedelta(hours=allocate_hours / 2)
                                end_time = midpoint + timedelta(hours=allocate_hours / 2)

                                if start_time < day_period_start:
                                    start_time = day_period_start
                                    end_time = start_time + timedelta(hours=allocate_hours)
                                elif end_time > day_period_end:
                                    end_time = day_period_end
                                    start_time = end_time - timedelta(hours=allocate_hours)

                                dummy_attendance = self.env['resource.calendar.attendance'].new({
                                    'duration_hours': allocate_hours,
                                })

                                intervals.append((start_time, end_time, dummy_attendance))

                            current_day += timedelta(days=1)

                        current_start_day += timedelta(days=7)

                    result_per_resource_id[resource.id] = Intervals(intervals, keep_distinct=True)
                else:
                    result_per_resource_id[resource.id] = res_intervals
        return result_per_resource_id

    def _handle_flexible_leave_interval(self, dt0, dt1, leave):
        """ Hook adapting the bounds of a resource-specific leave of a flexible resource.
        By default, the leave is extended to whole days: from 00:00 on the day of ``dt0`` to
        23:59:59.999999 on the day of ``dt1``, in their timezone.

        :param datetime dt0: leave start, localized in the resource timezone
        :param datetime dt1: leave end, localized in the resource timezone
        :param leave: the ``resource.calendar.leaves`` record
        :return: the adapted ``(dt0, dt1)``
        :rtype: tuple
        """
        tz = dt0.tzinfo  # Get the timezone information from dt0
        dt0 = datetime.combine(dt0.date(), time.min, tzinfo=tz)
        dt1 = datetime.combine(dt1.date(), time.max, tzinfo=tz)
        return dt0, dt1

    def _leave_intervals(self, start_dt, end_dt, resource=None, domain=None, tz=None):
        """ Single-resource shortcut of :meth:`_leave_intervals_batch`.

        :param resource: a ``resource.resource`` record, or ``None`` / empty for the
            calendar-level leaves (global leaves only, in the timezone of ``start_dt``)
        :param tz: unused, kept for compatibility; the resource timezone is used
        :rtype: :class:`~odoo.tools.intervals.Intervals`
        """
        if resource is None:
            resource = self.env['resource.resource']
        resources_per_tz = resource._get_resources_per_tz()
        return self._leave_intervals_batch(start_dt, end_dt, resources_per_tz=resources_per_tz, domain=domain)[resource.id]

    def _leave_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None):
        """ Return the leave intervals (``resource.calendar.leaves``) overlapping the period,
        clipped to ``[start_dt, end_dt]`` and expressed in the timezone of each resource.

        A resource gets its own leaves plus the global leaves (no ``resource_id``) of its
        company; the calendar-level entry (key ``False``) only gets global leaves. When
        ``self`` is set, only leaves of this calendar or without calendar are considered.
        Leaves of flexible resources go through :meth:`_handle_flexible_leave_interval`
        (whole days by default). Overlapping leaves are merged, the payload being the union
        of the leave records.

        :param datetime start_dt: timezone-aware start of the period
        :param datetime end_dt: timezone-aware end of the period
        :param dict resources_per_tz: ``{ZoneInfo: resource.resource recordset}``, see
            :meth:`_attendance_intervals_batch`
        :param list domain: domain (as a list) on ``resource.calendar.leaves``. ``None``
            means ``[('count_as', '=', 'absence')]``; any other value, even ``[]``, replaces
            that default, so leaves counted as working time are then included.
        :return: ``{resource_id: Intervals}`` for every resource of ``resources_per_tz``, plus
            the key ``False`` when ``self`` is set or ``resources_per_tz`` is empty
        :rtype: dict
        """
        assert start_dt.tzinfo and end_dt.tzinfo
        _logger.warning("The method _leave_intervals_batch is deprecated. Use TODO BEDO NEW NAME instead.")

        if domain is None:
            domain = [('count_as', '=', 'absence')]
        if self:
            domain = domain + [('calendar_id', 'in', [False] + self.ids)]

        all_resources = set()
        if not resources_per_tz or self:
            all_resources.add(self.env['resource.resource'])
            resources_per_tz = resources_per_tz or {start_dt.tzinfo: self.env['resource.resource']}
        if resources_per_tz:
            for _, resources in resources_per_tz.items():
                all_resources |= set(resources)

        # for the computation, express all datetimes in UTC
        # Public leave don't have a resource_id
        domain = domain + [
            ('resource_id', 'in', [False] + [r.id for r in all_resources]),
            ('date_from', '<=', end_dt.astimezone(UTC).replace(tzinfo=None)),
            ('date_to', '>=', start_dt.astimezone(UTC).replace(tzinfo=None)),
        ]

        # retrieve leave intervals in (start_dt, end_dt)
        result = defaultdict(list)
        tz_dates = {}
        all_leaves = self.env['resource.calendar.leaves'].search(domain)
        for leave in all_leaves:
            leave_resource = leave.resource_id
            leave_company = leave.company_id
            leave_date_from = leave.date_from
            leave_date_to = leave.date_to
            for tz, resources in resources_per_tz.items():
                for resource in chain(resources, (self.env['resource.resource'],) if self else ()):
                    if leave_resource.id not in [False, resource.id] or (not leave_resource and resource and resource.company_id != leave_company):
                        continue
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
                    dt0 = leave_date_from.astimezone(tz)
                    dt1 = leave_date_to.astimezone(tz)
                    if leave_resource and leave_resource._is_flexible():
                        dt0, dt1 = self._handle_flexible_leave_interval(dt0, dt1, leave)
                    result[resource.id].append((max(start, dt0), min(end, dt1), leave))
        return {r.id: Intervals(result[r.id]) for r in all_resources}

    def _work_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None, compute_leaves=True):
        """ Return the effective work intervals: attendance intervals minus leave intervals.
        This is the method to use (and the one to override, as ``hr_work_entry`` does) to

        :param datetime start_dt: timezone-aware start of the period
        :param datetime end_dt: timezone-aware end of the period
        :param dict resources_per_tz: ``{ZoneInfo: resource.resource recordset}``, see
            :meth:`_attendance_intervals_batch`
        :param list domain: leave domain passed to :meth:`_leave_intervals_batch` (``None``
            means leaves counted as absence). It does not filter attendances.
        :param bool compute_leaves: when ``False``, leaves are not deducted and the result
            equals :meth:`_attendance_intervals_batch`
        :return: ``{resource_id: Intervals}``, with the key ``False`` for the calendar-level
            result when ``self`` is set or ``resources_per_tz`` is empty. Intervals are
            expressed in each resource's timezone and carry attendance records.
        :rtype: dict
        """
        _logger.warning("The method _work_intervals_batch is deprecated. Use TODO BEDO NEW NAME instead.")
        all_resources = set()
        if not resources_per_tz or self:
        if resources_per_tz:
            for _, resources in resources_per_tz.items():
                all_resources |= set(resources)

        attendance_intervals = self._attendance_intervals_batch(start_dt, end_dt, resources_per_tz)
        if compute_leaves:
            leave_intervals = self._leave_intervals_batch(start_dt, end_dt, resources_per_tz, domain)
            return {
                r.id: (attendance_intervals[r.id] - leave_intervals[r.id]) for r in all_resources
            }
        return {
            r.id: attendance_intervals[r.id] for r in all_resources
        }

    def _unavailable_intervals(self, start_dt, end_dt, resource=None, domain=None, tz=None):
        """ Single-resource shortcut of :meth:`_unavailable_intervals_batch`.

        :param resource: a ``resource.resource`` record, or ``None`` / empty for the
            calendar-level result
        :param tz: unused, kept for compatibility
        :return: ``Intervals`` in UTC, empty for a flexible resource without leave
        """
        if resource is None:
            resource = self.env['resource.resource']
        resources_per_tz = resource._get_resources_per_tz()
        return self._unavailable_intervals_batch(
            start_dt, end_dt, resources_per_tz=resources_per_tz, domain=domain,
        ).get(resource.id, Intervals())

    def _unavailable_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None):
        """ Return the periods during which resources do not work: the complement of
        :meth:`_work_intervals_batch` within ``[start_dt, end_dt]``, expressed in UTC (used by
        Gantt views to grey out unavailable time).

        For a flexible resource (according to its own calendar), only its leaves are
        unavailable, and the resource has no key at all when it has no leave (callers treat
        that absence as "no unavailability").

        :param datetime start_dt: timezone-aware start of the period
        :param datetime end_dt: timezone-aware end of the period
        :param dict resources_per_tz: ``{ZoneInfo: resource.resource recordset}``, see
            :meth:`_attendance_intervals_batch`
        :param list domain: leave domain, see :meth:`_leave_intervals_batch`
        :return: ``{resource_id: Intervals}`` in UTC, with the key ``False`` when ``self`` is
            set or ``resources_per_tz`` is empty
        :rtype: dict
        """
        all_resources = set()
        if not resources_per_tz or self:
            all_resources.add(self.env['resource.resource'])
        if resources_per_tz:
            for _, resources in resources_per_tz.items():
                all_resources |= set(resources)
        resources_work_intervals = self._work_intervals_batch(start_dt, end_dt, resources_per_tz, domain)
        leaves = None
        result = {}
        for resource in all_resources:
            if resource and resource._is_flexible():
                if leaves is None:
                    leaves = self._leave_intervals_batch(start_dt, end_dt, resources_per_tz, domain)
                if res_leaves := leaves[resource.id]:
                    result[resource.id] = Intervals([
                        (start.astimezone(UTC), stop.astimezone(UTC), meta)
                        for start, stop, meta in res_leaves
                    ])
                continue
            work_intervals = resources_work_intervals[resource.id]
            utc_work_intervals = []
            for (start, stop, meta) in work_intervals:
                utc_work_intervals.append((start.astimezone(UTC), stop.astimezone(UTC), meta))

            utc_work_intervals = Intervals(utc_work_intervals)
            full_interval_UTC = Intervals([(
                start_dt.astimezone(UTC),
                end_dt.astimezone(UTC),
                self.env['resource.calendar'],
            )])

            result[resource.id] = full_interval_UTC - utc_work_intervals
        return result

    def _get_attendance_intervals_days_data(self, attendance_intervals):
        """ Convert work intervals (typically the output of :meth:`_work_intervals_batch`
        for one resource) into a duration in days and hours.

        Intervals are split per calendar day (in their own timezone). For each day:

        - if this calendar has duration-based attendances on that day, the day counts for
          ``hours / sum(their duration_hours)`` (proportional);
        - otherwise it counts for 0.5 day if its hours are at most 3/4 of
          :meth:`_get_reference_hours_per_day`, else for 1 day.

        The payload of the intervals is ignored. ``self`` may be empty: then any day with
        hours counts as 1.

        :param attendance_intervals: iterable of ``(start, stop, records)`` with
            timezone-aware datetimes, e.g. an :class:`~odoo.tools.intervals.Intervals`
        :return: ``{'days': float, 'hours': float}``, days rounded to 0.001
        :rtype: dict
        """
        if self:
            self.ensure_one()
        day_hours = defaultdict(float)
        day_days = defaultdict(float)
        for start, stop, _ in attendance_intervals:
            # If the interval covers only a part of the original attendance, we
            # take durations in days proportionally to what is left of the interval.
            # an interval synthesized for a fully flexible calendar can span several
            # calendar days at once: split it at midnight so each day gets its own
            # bucket (no empty bucket for an interval ending at midnight)
            day_start = start
            while day_start < stop:
                next_day_start = datetime.combine(day_start.date() + timedelta(days=1), time.min, tzinfo=day_start.tzinfo)
                day_end = min(stop, next_day_start)
                day_hours[day_start.date()] += (day_end - day_start).total_seconds() / 3600
                day_start = day_end

        duration_based_attendances = self.attendance_ids.filtered('duration_based')
        for day, hours in day_hours.items():
            if attendances := duration_based_attendances._filter_by_date(day):
                hours_per_day = sum(attendances.mapped('duration_hours'))
                day_days[day] += hours / hours_per_day if hours_per_day else 0
            else:
                # A day is only a full one above 3 / 4 of the theoretical day, below that it is half a day.
                reference_hours = self._get_reference_hours_per_day(day) if self else self.hours_per_day
                day_days[day] = 0.5 if hours <= reference_hours * 3 / 4 else 1

        return {
            # Round the number of days to the closest thousandth of a day.
            'days': float_round(sum(day_days[day] for day in day_days), precision_rounding=0.001),
            'hours': sum(day_hours.values()),
        }

    def _get_reference_hours_per_day(self, day):
        """ Return the number of hours ``day`` is theoretically made of, used as the full-day
        reference by :meth:`_get_attendance_intervals_days_data`. Defaults to the calendar's
        average ``hours_per_day``; overridden by ``hr_work_entry`` to include attendances
        counted as absence.

        :param date day: the day to evaluate
        :rtype: float
        """
        self.ensure_one()
        return self.hours_per_day

    def _get_closest_work_time(self, dt, match_end=False, resource=None, search_range=None, compute_leaves=True):
        """ Return the work interval boundary closest to ``dt`` within the search range: the
        closest interval start, or the closest interval end when ``match_end`` is set.

        Work intervals come from :meth:`_work_intervals_batch` for ``resource``, in the
        resource timezone. Without resource, the calendar-level intervals are used and the
        attendance hours are interpreted in UTC.

        :param datetime dt: timezone-aware reference datetime
        :param bool match_end: look for interval ends instead of interval starts
        :param resource: ``resource.resource`` record, or ``None``
        :param search_range: ``(start, end)`` timezone-aware datetimes; defaults to the whole
            day of ``dt`` in the resource timezone
        :param bool compute_leaves: deduct leaves from the work intervals
        :return: the closest boundary (in the resource timezone), or ``None`` if ``dt`` is
            outside the search range or there is no work interval in it
        :rtype: datetime | None
        :raises ValueError: if ``dt`` or ``search_range`` are naive
        """
        def interval_dt(interval):
            return interval[1 if match_end else 0]

        tz = resource.tz if resource else 'UTC'
        if resource is None:
            resource = self.env['resource.resource']

        if not dt.tzinfo or (search_range and not (search_range[0].tzinfo and search_range[1].tzinfo)):
            raise ValueError(self.env._('Provided datetimes needs to be timezoned'))

        dt = dt.astimezone(ZoneInfo(tz))

        if not search_range:
            range_start = dt + relativedelta(hour=0, minute=0, second=0)
            range_end = dt + relativedelta(days=1, hour=0, minute=0, second=0)
        else:
            range_start, range_end = search_range

        if not range_start <= dt <= range_end:
            return None
        resources_per_tz = resource._get_resources_per_tz()
        work_intervals = sorted(
            self._work_intervals_batch(range_start, range_end, resources_per_tz, compute_leaves=compute_leaves)[resource.id],
            key=lambda i: abs(interval_dt(i) - dt),
        )
        return interval_dt(work_intervals[0]) if work_intervals else None

    def _get_unusual_days(self, start_dt, end_dt, company_id=False, resource=None):
        """ Tell, for each day between ``start_dt`` and ``end_dt``, whether it is an
        "unusual" day, i.e. a day without work (weekend, public holiday...). Used by calendar
        and date picker widgets to grey out days.

        Days are evaluated with the calendar-level work intervals (global leaves deducted),
        in the timezone of ``start_dt``.
        For a flexible ``resource``, a day is unusual only if the resource has a leave on it.
        Only leaves counted as absence are considered: a leave counted as working time
        (e.g. a training) does not make a day unusual.

        :param datetime start_dt: start of the period; naive means UTC
        :param datetime end_dt: end of the period (its day included); naive means UTC
        :param company_id: optional ``res.company`` record restricting the leaves to that
            company or to no company
        :param resource: optional ``resource.resource`` record, only used for flexible ones
        :return: ``{'YYYY-MM-DD': bool}``, ``True`` for unusual days
        :rtype: dict
        """
        if self:
            self.ensure_one()
        if not start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=UTC)
        if not end_dt.tzinfo:
            end_dt = end_dt.replace(tzinfo=UTC)

        domain = [('count_as', '=', 'absence')]
        if company_id:
            domain += [('company_id', 'in', (company_id.id, False))]
        if resource and resource._is_flexible():
            leave_intervals = self._leave_intervals_batch(start_dt, end_dt, domain=domain, resources_per_tz=resource._get_resources_per_tz())[resource.id]
            works = set()
            for start_int, end_int, _ in leave_intervals:
                works.update(start_int.date() + timedelta(days=i) for i in range((end_int.date() - start_int.date()).days + 1))
            return {fields.Date.to_string(day.date()): (day.date() in works) for day in rrule(DAILY, start_dt, until=end_dt)}
        works = {d[0].date() for d in self._work_intervals_batch(start_dt, end_dt, domain=domain)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, start_dt, until=end_dt)}

    def _get_default_attendance_ids(self, company_id=None):
        """ Return ``attendance_ids`` commands copying the attendances of the company's fixed
        calendar, or, by default, 5 duration-based days of 8 hours (Monday to Friday).

        :param company_id: ``res.company`` record, or ``None``
        :rtype: list
        """
        if company_id and company_id.resource_calendar_id.calendar_type == "fixed" and (attendances := company_id.resource_calendar_id.attendance_ids):
            return [Command.clear()] + [Command.create(attendance) for attendance in attendances._to_dict()]
        return [Command.clear()] + [
            Command.create({'dayofweek': str(dayofweek), 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0})
            for dayofweek in range(5)
        ]

    # --------------------------------------------------
    # External API
    # --------------------------------------------------

    def get_work_hours_count(self, start_dt, end_dt, compute_leaves=True, domain=None):
        """ Return the number of calendar-level work hours between two dates or datetimes
        (no resource: only global leaves are deducted).

        Attendance hours are interpreted in the timezone of ``start_dt`` after conversion:
        dates and naive datetimes are put in the company timezone, aware datetimes keep
        their own timezone.

        :param start_dt: ``date`` (from 00:00 in the company timezone) or ``datetime``
            (naive means UTC)
        :param end_dt: ``date`` (until 23:59:59.999999 in the company timezone) or
            ``datetime`` (naive means UTC)
        :param bool compute_leaves: deduct global leaves
        :param list domain: leave domain, ``None`` means ``[('count_as', '=', 'absence')]``,
            see :meth:`_leave_intervals_batch`
        :rtype: float
        """
        self.ensure_one()

        # datetime is also an instance of date
        assert isinstance(start_dt, date)
        assert isinstance(end_dt, date)

        tz = ZoneInfo(self.env.company.tz)

        # convert to datetime if object passed is date
        if not isinstance(start_dt, datetime):
            start_dt = datetime.combine(start_dt, time.min, tz)
        if not isinstance(end_dt, datetime):
            end_dt = datetime.combine(end_dt, time.max, tz)

        # Set timezone in company tz if no timezone is explicitly given
        if not start_dt.tzinfo:
            start_dt = start_dt.astimezone(tz)
        if not end_dt.tzinfo:
            end_dt = end_dt.astimezone(tz)

        if compute_leaves:
            intervals = self._work_intervals_batch(start_dt, end_dt, domain=domain)[False]
        else:
            intervals = self._attendance_intervals_batch(start_dt, end_dt)[False]

        return sum(
            (stop - start).total_seconds() / 3600
            for start, stop, meta in intervals
        )

    def get_work_duration_data(self, from_datetime, to_datetime, compute_leaves=True, domain=None):
        """ Return the calendar-level working duration of a period, in days and hours, only
        based on this calendar (no resource: only global leaves are deducted). Days are
        computed by :meth:`_get_attendance_intervals_days_data`.

        Attendance hours are interpreted in the timezone of ``from_datetime`` (UTC if naive).

        :param datetime from_datetime: start of the period, naive means UTC
        :param datetime to_datetime: end of the period, naive means UTC
        :param bool compute_leaves: deduct global leaves
        :param list domain: with ``compute_leaves``, the leave domain (``None`` means
            ``[('count_as', '=', 'absence')]``); without it, a domain on
            ``resource.calendar.attendance`` filtering the attendances
        :return: ``{'days': float, 'hours': float}``
        :rtype: dict
        """
        self.ensure_one()
        # naive datetimes are made explicit in UTC
        from_datetime = localized(from_datetime)
        to_datetime = localized(to_datetime)

        # actual hours per day
        if compute_leaves:
            intervals = self._work_intervals_batch(from_datetime, to_datetime, domain=domain)[False]
        else:
            intervals = self._attendance_intervals_batch(from_datetime, to_datetime, domain=domain)[False]

        return self._get_attendance_intervals_days_data(intervals)

    def plan_hours(self, hours, day_dt, compute_leaves=False, domain=None, resource=None):
        """ Return the datetime reached after working ``hours`` hours from ``day_dt`` according
        to this calendar (going backwards if ``hours`` is negative). With ``hours=0``, return
        ``day_dt`` if it is within work time, else the start of the next work interval.

        Computation happens in the timezone of ``resource`` (company timezone without
        resource), by windows of 14 days, for at most 100 windows.

        :param float hours: number of work hours to plan, negative to plan backwards
        :param datetime day_dt: starting point; naive means UTC
        :param bool compute_leaves: deduct leaves (those of ``resource`` and global ones);
            without it, the calendar-level attendances are used and ``resource`` only gives
            the timezone
        :param list domain: leave domain, see :meth:`_leave_intervals_batch`
        :param resource: optional ``resource.resource`` record
        :return: the resulting datetime, in the timezone of ``day_dt`` (naive UTC if
            ``day_dt`` is naive), or ``False`` if not found within the search range
        :rtype: datetime | bool
        """
        revert = to_timezone(day_dt.tzinfo)
        day_dt = day_dt.astimezone(ZoneInfo(resource.tz if resource else self.env.company.tz))

        if resource is None:
            resource = self.env['resource.resource']

        # which method to use for retrieving intervals
        if compute_leaves:
            resources_per_tz = resource._get_resources_per_tz()
            get_intervals = partial(self._work_intervals_batch, domain=domain, resources_per_tz=resources_per_tz)
            resource_id = resource.id
        else:
            get_intervals = self._attendance_intervals_batch
            resource_id = False

        if hours >= 0:
            delta = timedelta(days=14)
            for n in range(100):
                dt = day_dt + delta * n
                for start, stop, _meta in get_intervals(dt, dt + delta)[resource_id]:
                    interval_hours = (stop - start).total_seconds() / 3600
                    if hours <= interval_hours:
                        return revert(start + timedelta(hours=hours))
                    hours -= interval_hours
            return False
        hours = abs(hours)
        delta = timedelta(days=14)
        for n in range(100):
            dt = day_dt - delta * n
            for start, stop, _meta in reversed(get_intervals(dt - delta, dt)[resource_id]):
                interval_hours = (stop - start).total_seconds() / 3600
                if hours <= interval_hours:
                    return revert(stop - timedelta(hours=hours))
                hours -= interval_hours
        return False

    def plan_days(self, days, day_dt, compute_leaves=False, domain=None):
        """ Return the end of the first work interval of the ``days``-th work day counted
        from ``day_dt`` (the day of ``day_dt`` included if it has work time after
        ``day_dt``), or, for a negative ``days``, the start of the last work interval of the
        ``abs(days)``-th work day counted backwards. ``days=0`` returns ``day_dt``.

        Beware: with several attendances per day (e.g. a lunch break), the result is the end
        of the morning attendance of the last day, not the end of that day.

        Calendar-level only (no resource, only global leaves), computed in the company
        timezone by windows of 14 days, for at most 100 windows.

        :param int days: number of work days to plan, negative to plan backwards
        :param datetime day_dt: starting point; naive means UTC
        :param bool compute_leaves: deduct global leaves
        :param list domain: leave domain, see :meth:`_leave_intervals_batch`
        :return: the resulting datetime, in the timezone of ``day_dt`` (naive UTC if
            ``day_dt`` is naive), or ``False`` if not found within the search range
        :rtype: datetime | bool
        """
        revert = to_timezone(day_dt.tzinfo)
        day_dt = day_dt.astimezone(ZoneInfo(self.env.company.tz))

        # which method to use for retrieving intervals
        if compute_leaves:
            get_intervals = partial(self._work_intervals_batch, domain=domain)
        else:
            get_intervals = self._attendance_intervals_batch

        if days > 0:
            found = set()
            delta = timedelta(days=14)
            for n in range(100):
                dt = day_dt + delta * n
                for start, stop, _meta in get_intervals(dt, dt + delta)[False]:
                    found.add(start.date())
                    if len(found) == days:
                        return revert(stop)
            return False

        if days < 0:
            days = abs(days)
            found = set()
            delta = timedelta(days=14)
            for n in range(100):
                dt = day_dt - delta * n
                for start, _stop, _meta in reversed(get_intervals(dt - delta, dt)[False]):
                    found.add(start.date())
                    if len(found) == days:
                        return revert(start)
            return False

        return revert(day_dt)

    def _works_on_date(self, date):
        """ Return whether this calendar has a work attendance (see
        ``resource.calendar.attendance._is_work_period``) on ``date``. Always ``True`` for
        flexible calendars. Leaves are not considered.

        :param date date: the day to check
        :rtype: bool
        """
        # a flexible calendar has no predefined slots to check a specific date against
        if self._is_flexible():
            return True
        return bool(self.attendance_ids._filter_by_date(date, lambda a: a._is_work_period()))

    def _get_attendances_by_date(self, date_from, date_to, domain=None):  # TODO BEDO grep the calls to this and check if can't be batched
        self.ensure_one()
        return self._get_attendances_by_date_batch(date_from, date_to, domain)[self]

    def _get_attendances_by_date_batch(self, date_from, date_to, domain=None):
        """
        For each calendar in self, get the attendances between date_from and date_to, grouped by day, as a recordset of resource.calendar.attendance.
            - For variable schedule, only attendances with a date are considered. If an attendance has a recurrency rule, it will be repeated on the corresponding days.
            - For fixed schedule, only attendances without a date are considered. They will be grouped by their dayofweek and returned on the corresponding days.

        - Undated attendances (``fixed`` calendars) apply on every day matching their
          ``dayofweek``.
        - Dated attendances (``variable`` calendars) apply on their ``date`` and, when
          recurring, on every occurrence of their recurrence rule up to
          ``recurrency_until``, except excluded occurrences.

        :param date date_from: first day of the period (included)
        :param date date_to: last day of the period (included)
        :param domain: optional domain on ``resource.calendar.attendance``
        :return: ``{date: resource.calendar.attendance recordset}`` with one key per day of
            the period, possibly mapped to an empty recordset (a ``defaultdict``)
        :rtype: dict
        """
        result = defaultdict(lambda: defaultdict(lambda: self.env['resource.calendar.attendance']))

        domain_fixed = Domain([('date', '=', False)])
        domain_variable_recurrency = Domain([
            ('recurrency', '=', True),
            ('date', '<=', date_to),
            ('recurrency_until', '>=', date_from),
        ])
        domain_variable_adhoc = Domain([
            ('recurrency', '=', False),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ])
        domain_to_fetch = Domain.AND([
            domain or Domain.TRUE,
            Domain.OR([
                domain_fixed,
                domain_variable_recurrency,
                domain_variable_adhoc,
            ]),
            Domain('calendar_id', 'in', self.ids),
        ])
        all_attendances = self.env["resource.calendar.attendance"].search_fetch(domain_to_fetch)
        for calendar, attendances in all_attendances.grouped('calendar_id').items():
            recurrent_attendances = attendances.filtered("recurrency")
            ad_hoc_attendances = (attendances - recurrent_attendances).grouped(lambda a: a.date or a.dayofweek)
            for day in rrule(DAILY, date_from, until=date_to):
                result[calendar][day.date()] = ad_hoc_attendances.get(day.date(), self.env['resource.calendar.attendance'])
                result[calendar][day.date()] += ad_hoc_attendances.get(str(day.weekday()), self.env['resource.calendar.attendance'])
                result[calendar][day.date()] += recurrent_attendances._filter_by_date(day.date())
        return result

    def get_attendances(self, date_from, date_to, fields_to_fetch, domain=None):
        """ Public (RPC) variant of :meth:`_get_attendances_by_date` used by the calendar
        editor: return each attendance occurring in the period once, read with
        ``fields_to_fetch``.

        :param date_from: first day, as a ``date`` or a ``'YYYY-MM-DD'`` string
        :param date_to: last day, as a ``date`` or a ``'YYYY-MM-DD'`` string
        :param list fields_to_fetch: field names to read
        :param domain: optional domain on ``resource.calendar.attendance``
        :return: list of dicts with the read values, plus ``'date'`` (first occurrence in
            the period) and ``'other_dates'`` (list of the next occurrences)
        :rtype: list
        """
        date_from = fields.Date.from_string(date_from)
        date_to = fields.Date.from_string(date_to)
        attendances_per_date = self._get_attendances_by_date(date_from, date_to, domain)
        formatted_attendances = defaultdict(self.env["resource.calendar.attendance"].browse)
        for att_date, attendances in attendances_per_date.items():
            new_formatted_attendances = attendances._read_format(fnames=fields_to_fetch)
            for attendance in new_formatted_attendances:
                if formatted_attendances[attendance['id']]:
                    formatted_attendances[attendance['id']]['other_dates'].append(att_date)
                else:
                    attendance['date'] = att_date
                    attendance['other_dates'] = []
                    formatted_attendances[attendance['id']] = attendance
        return list(formatted_attendances.values())

    # --------------------------------------------------
    # New API
    # --------------------------------------------------

    def _attendance_intervals(self, dt_from, dt_to, domain=None, tz_list=[], availability=False):
        """
        Get the attendances between dt_from and dt_to, as intervals linked to records of resource.calendar.attendance.
            - For variable schedule, only attendances with a date are considered. If an attendance has a recurrency rule, it will be repeated on the corresponding days.
            - For fixed schedule, only attendances without a date are considered. They will be grouped by their dayofweek and returned on the corresponding days.
        As calendars aren't bound to timezones, the return intervals are given back with naive datetimes.

        :param dt_from: start date of the period (included).
        :param dt_to: end date of the period (included)
        :param domain: optional domain to filter attendances
        :param availability: optional attribute for availability computation.
            If attendances do not have any start/end specified, it is technically not possible to get them a real interval.
            When `availability` is False, it will try to fit the attendance around noon and create an interval respecting the duration
            When `availability` is True, it will return the entire day as the employee is supposedly present the entire day
        :return dict:
        """
        dt_from = dt_from.replace(tzinfo=None)
        dt_to = dt_to.replace(tzinfo=None)
        intervals_per_calendar = defaultdict(dict)
        attendances_per_calendar = self._get_attendances_by_date_batch(dt_from.date(), dt_to.date(), domain)
        for calendar, att_per_date in attendances_per_calendar.items():
            interval_tuple_list = []
            for att_date, attendances in att_per_date.items():
                if not attendances:
                    continue
                att_start = time.min
                if attendances[0].duration_based and not availability:
                    total_duration = sum(attendances.mapped('duration_hours'))
                    att_start = float_to_time(12 - total_duration / 2)
                    # This part is to avoid having no attendances when we take specific schedules on a day;
                    # For example, attendances from 9PM to 11PM should return 2 hours with a duration-based, 8 hours/day
                    # schedule. Without this, the expected attendances would be 8AM-4PM and the period for which we called
                    # the method would return 0. Same reasoning the other way around, if we look for attendances at 2AM-4AM.
                    if att_date == dt_from.date():
                        att_start = dt_from.time()
                    elif att_date == dt_to.date():
                        att_start = time.min
                for att in attendances:
                    if not att.duration_based:
                        hour_start = float_to_time(att.hour_from)
                        hour_stop = float_to_time(att.hour_to)
                    elif not availability:
                        hour_start = att_start
                        hour_stop = float_to_time(min(time_to_float(att_start) + att.duration_hours, 24))
                        att_start = hour_stop
                        if hour_start == hour_stop:
                            break
                    else:
                        start = datetime.combine(att_date, time.min)
                        stop = datetime.combine(att_date, time.max)
                        interval_tuple_list.append((start, stop, att))
                        # When checking availabilities, the information regarding the attendance record don't really
                        # matter, so we can skip other attendances of the day.
                        break
                    start = datetime.combine(att_date, hour_start)
                    stop = datetime.combine(att_date, hour_stop)
                    interval_tuple_list.append((start, stop, att))
            intervals_per_calendar[calendar] = Intervals(interval_tuple_list, keep_distinct=True) & Intervals([(dt_from, dt_to, self.env['resource.calendar.attendance'])]) # TODO BEDO
        return intervals_per_calendar

