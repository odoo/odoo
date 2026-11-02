from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError


WEEKDAYS = [
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
]

WEEK_TYPES = [
    ('0', 'Week 1'),
    ('1', 'Week 2'),
]


class PresenlyWorkLocationSchedule(models.Model):
    _name = 'presenly.work.location.schedule'
    _description = 'Employee Work Location Time Slot'
    _order = (
        'employee_id, schedule_type desc, schedule_date, weekday, week_type, '
        'hour_from, id'
    )

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='cascade', index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        'res.company', related='employee_id.company_id', store=True,
        readonly=True, index=True,
    )
    work_location_id = fields.Many2one(
        'hr.work.location', required=True, ondelete='restrict', index=True,
        check_company=True,
    )
    calendar_id = fields.Many2one(
        'resource.calendar', compute='_compute_calendar_context',
        string='Working Hours', readonly=True,
    )
    calendar_two_weeks = fields.Boolean(
        compute='_compute_calendar_context', readonly=True,
    )
    schedule_type = fields.Selection([
        ('weekly', 'Weekly'),
        ('date', 'Specific Date'),
    ], required=True, default='weekly', index=True)
    weekday = fields.Selection(WEEKDAYS, default='0', index=True)
    week_type = fields.Selection(
        WEEK_TYPES, string='Calendar Week', index=True,
        help='Required when the employee uses a two-week Working Hours calendar.',
    )
    schedule_date = fields.Date(index=True)
    date_start = fields.Date(string='Valid From')
    date_end = fields.Date(string='Valid Until')
    hour_from = fields.Float(required=True, default=8.0, string='Start Time')
    hour_to = fields.Float(required=True, default=17.0, string='End Time')
    check_in_tolerance_minutes = fields.Integer(
        default=30, string='Check-In Tolerance (minutes)',
        help='How early this slot may be selected for check-in.',
    )
    calendar_sync_state = fields.Selection([
        ('valid', 'Synced'),
        ('flexible', 'Flexible Hours'),
        ('no_calendar', 'No Working Hours'),
        ('outside', 'Outside Working Hours'),
    ], compute='_compute_calendar_sync', string='Working Hours Status')
    calendar_sync_message = fields.Char(
        compute='_compute_calendar_sync', string='Working Hours Details',
    )
    active = fields.Boolean(default=True)

    _valid_hours = models.Constraint(
        'CHECK(hour_from >= 0 AND hour_from < hour_to AND hour_to <= 24)',
        'The schedule must have a valid start and end time within one day.',
    )
    _valid_period = models.Constraint(
        'CHECK(date_end IS NULL OR date_start IS NULL OR date_end >= date_start)',
        'Valid Until must be on or after Valid From.',
    )
    _nonnegative_tolerance = models.Constraint(
        'CHECK(check_in_tolerance_minutes >= 0)',
        'Check-in tolerance cannot be negative.',
    )

    @api.depends(
        'employee_id', 'work_location_id', 'schedule_type', 'weekday',
        'week_type', 'schedule_date', 'hour_from', 'hour_to',
    )
    def _compute_name(self):
        weekday_labels = dict(WEEKDAYS)
        week_labels = dict(WEEK_TYPES)
        for slot in self:
            day = (
                fields.Date.to_string(slot.schedule_date)
                if slot.schedule_type == 'date' and slot.schedule_date
                else weekday_labels.get(slot.weekday, '')
            )
            week = (
                f' ({week_labels.get(slot.week_type)})'
                if slot.schedule_type == 'weekly'
                and slot.calendar_two_weeks and slot.week_type
                else ''
            )
            slot.name = (
                f'{slot.employee_id.name or "Employee"} - '
                f'{day}{week} {slot._format_hour(slot.hour_from)}–'
                f'{slot._format_hour(slot.hour_to)} - '
                f'{slot.work_location_id.name or "Location"}'
            )

    @api.depends(
        'employee_id', 'employee_id.current_version_id',
        'employee_id.current_version_id.resource_calendar_id',
        'schedule_type', 'schedule_date',
    )
    def _compute_calendar_context(self):
        for slot in self:
            calendar = slot._presenly_calendar()
            slot.calendar_id = calendar
            slot.calendar_two_weeks = calendar.two_weeks_calendar

    @api.depends(
        'employee_id', 'schedule_type', 'weekday', 'week_type', 'schedule_date',
        'hour_from', 'hour_to', 'employee_id.current_version_id',
        'employee_id.current_version_id.resource_calendar_id',
        'employee_id.current_version_id.resource_calendar_id.flexible_hours',
        'employee_id.current_version_id.resource_calendar_id.two_weeks_calendar',
        'employee_id.current_version_id.resource_calendar_id.attendance_ids.dayofweek',
        'employee_id.current_version_id.resource_calendar_id.attendance_ids.week_type',
        'employee_id.current_version_id.resource_calendar_id.attendance_ids.hour_from',
        'employee_id.current_version_id.resource_calendar_id.attendance_ids.hour_to',
        'employee_id.current_version_id.resource_calendar_id.attendance_ids.day_period',
        'employee_id.current_version_id.resource_calendar_id.attendance_ids.display_type',
    )
    def _compute_calendar_sync(self):
        for slot in self:
            state, message = slot._presenly_calendar_sync_values()
            slot.calendar_sync_state = state
            slot.calendar_sync_message = message

    @staticmethod
    def _format_hour(value):
        hour = int(value or 0)
        minute = round(((value or 0) - hour) * 60)
        if minute == 60:
            hour += 1
            minute = 0
        return f'{hour:02d}:{minute:02d}'

    @staticmethod
    def _merge_intervals(intervals):
        merged = []
        for start, stop in sorted(intervals):
            if not merged or start > merged[-1][1] + 0.000001:
                merged.append([start, stop])
            else:
                merged[-1][1] = max(merged[-1][1], stop)
        return [(start, stop) for start, stop in merged]

    def _presenly_calendar(self):
        self.ensure_one()
        if not self.employee_id:
            return self.env['resource.calendar']
        if self.schedule_type == 'date' and self.schedule_date:
            version = self.employee_id.sudo()._get_version(self.schedule_date)
            if version and version.resource_calendar_id:
                return version.resource_calendar_id
        return self.employee_id.sudo().resource_calendar_id

    def _presenly_calendar_intervals(self):
        """Return local-hour intervals applicable to this slot."""
        self.ensure_one()
        calendar = self._presenly_calendar()
        if not calendar or calendar.flexible_hours:
            return []
        target_weekday = (
            str(self.schedule_date.weekday())
            if self.schedule_type == 'date' and self.schedule_date
            else self.weekday
        )
        target_week_type = False
        if calendar.two_weeks_calendar:
            if self.schedule_type == 'date' and self.schedule_date:
                target_week_type = str(
                    self.env['resource.calendar.attendance'].get_week_type(
                        self.schedule_date
                    )
                )
            else:
                target_week_type = self.week_type
        lines = calendar.attendance_ids.filtered(
            lambda line: line._is_work_period()
            and line.dayofweek == target_weekday
            and (
                not calendar.two_weeks_calendar
                or line.week_type == target_week_type
            )
        )
        return self._merge_intervals([
            (line.hour_from, line.hour_to) for line in lines
        ])

    def _presenly_calendar_sync_values(self):
        self.ensure_one()
        calendar = self._presenly_calendar()
        if not calendar:
            return (
                'no_calendar',
                'Select Working Hours on the Employee before assigning locations.',
            )
        if calendar.flexible_hours:
            return (
                'flexible',
                'The employee uses Flexible Hours; fixed-hour containment is not required.',
            )
        if (
            self.schedule_type == 'weekly'
            and calendar.two_weeks_calendar
            and not self.week_type
        ):
            return (
                'outside',
                'Select Week 1 or Week 2 to match the two-week Working Hours calendar.',
            )
        intervals = self._presenly_calendar_intervals()
        if any(
            self.hour_from >= start - 0.000001
            and self.hour_to <= stop + 0.000001
            for start, stop in intervals
        ):
            return ('valid', 'This location slot is contained in Working Hours.')
        interval_label = ', '.join(
            f'{self._format_hour(start)}–{self._format_hour(stop)}'
            for start, stop in intervals
        ) or 'no working period'
        return (
            'outside',
            f'The location slot must fit within Working Hours: {interval_label}.',
        )

    def _presenly_is_within_working_hours(self):
        self.ensure_one()
        return self._presenly_calendar_sync_values()[0] in ('valid', 'flexible')

    @api.onchange('schedule_type')
    def _onchange_schedule_type(self):
        if self.schedule_type == 'weekly':
            self.schedule_date = False
        else:
            self.date_start = False
            self.date_end = False
            self.week_type = False

    @api.onchange(
        'employee_id', 'schedule_type', 'weekday', 'week_type', 'schedule_date'
    )
    def _onchange_working_hours(self):
        if not self.employee_id:
            return
        if not self.work_location_id:
            self.work_location_id = self.employee_id.work_location_id
        calendar = self._presenly_calendar()
        if (
            self.schedule_type == 'weekly'
            and calendar.two_weeks_calendar and not self.week_type
        ):
            self.week_type = '0'
        intervals = self._presenly_calendar_intervals()
        if intervals and not any(
            self.hour_from >= start - 0.000001
            and self.hour_to <= stop + 0.000001
            for start, stop in intervals
        ):
            self.hour_from, self.hour_to = intervals[0]

    @api.constrains(
        'employee_id', 'company_id', 'work_location_id', 'schedule_type',
        'weekday', 'week_type', 'schedule_date', 'date_start', 'date_end',
        'hour_from', 'hour_to', 'active',
    )
    def _check_schedule(self):
        for slot in self:
            if slot.work_location_id.company_id != slot.company_id:
                raise ValidationError(
                    'Employee and Work Location must belong to the same company.'
                )
            if slot.schedule_type == 'weekly' and slot.weekday is False:
                raise ValidationError('Weekday is required for a weekly schedule.')
            if slot.schedule_type == 'date' and not slot.schedule_date:
                raise ValidationError('Date is required for a specific-date schedule.')
            # A calendar change may make an existing slot invalid. Managers
            # must still be able to archive that conflict from the integrated UI.
            if not slot.active:
                continue
            state, message = slot._presenly_calendar_sync_values()
            if state not in ('valid', 'flexible'):
                raise ValidationError(message)
            domain = [
                ('id', '!=', slot.id),
                ('active', '=', True),
                ('employee_id', '=', slot.employee_id.id),
                ('schedule_type', '=', slot.schedule_type),
                ('hour_from', '<', slot.hour_to),
                ('hour_to', '>', slot.hour_from),
            ]
            if slot.schedule_type == 'date':
                domain.append(('schedule_date', '=', slot.schedule_date))
                overlapping = self.search(domain, limit=1)
            else:
                domain.extend([
                    ('weekday', '=', slot.weekday),
                    ('week_type', '=', slot.week_type or False),
                ])
                candidates = self.search(domain)
                overlapping = candidates.filtered(
                    lambda candidate: (
                        not slot.date_end
                        or not candidate.date_start
                        or candidate.date_start <= slot.date_end
                    ) and (
                        not candidate.date_end
                        or not slot.date_start
                        or candidate.date_end >= slot.date_start
                    )
                )[:1]
            if overlapping:
                raise ValidationError(
                    'Work location time slots for one employee cannot overlap.'
                )

    def _matches_local_datetime(self, local_datetime):
        self.ensure_one()
        local_date = local_datetime.date()
        if self.schedule_type == 'date':
            if self.schedule_date != local_date:
                return False
        else:
            if self.weekday != str(local_date.weekday()):
                return False
            calendar = self._presenly_calendar()
            if calendar.two_weeks_calendar:
                actual_week_type = str(
                    self.env['resource.calendar.attendance'].get_week_type(
                        local_date
                    )
                )
                if self.week_type != actual_week_type:
                    return False
            if self.date_start and local_date < self.date_start:
                return False
            if self.date_end and local_date > self.date_end:
                return False
        local_hour = local_datetime.hour + local_datetime.minute / 60.0
        tolerance = self.check_in_tolerance_minutes / 60.0
        return self.hour_from - tolerance <= local_hour < self.hour_to

    def _covers_date(self, target_date):
        self.ensure_one()
        if self.schedule_type == 'date':
            return self.schedule_date == target_date
        calendar = self._presenly_calendar()
        if calendar.two_weeks_calendar:
            actual_week_type = str(
                self.env['resource.calendar.attendance'].get_week_type(target_date)
            )
            if self.week_type != actual_week_type:
                return False
        return (
            self.weekday == str(target_date.weekday())
            and (not self.date_start or self.date_start <= target_date)
            and (not self.date_end or self.date_end >= target_date)
        )

    @api.model
    def _calendar_template_periods(self, employee):
        """Return merged weekly Working Hours periods for generator/coverage."""
        calendar = employee.sudo().resource_calendar_id
        if not calendar or calendar.flexible_hours:
            return []
        grouped = defaultdict(list)
        for line in calendar.attendance_ids.filtered(
            lambda attendance: attendance._is_work_period()
        ):
            week_type = line.week_type if calendar.two_weeks_calendar else False
            grouped[(line.dayofweek, week_type)].append(
                (line.hour_from, line.hour_to)
            )
        periods = []
        for (weekday, week_type), intervals in grouped.items():
            for hour_from, hour_to in self._merge_intervals(intervals):
                periods.append({
                    'weekday': weekday,
                    'week_type': week_type,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                })
        return sorted(
            periods,
            key=lambda item: (
                int(item['weekday']), item['week_type'] or '', item['hour_from']
            ),
        )
