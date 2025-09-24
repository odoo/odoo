# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import timezone, utc

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, models, fields
from odoo.exceptions import ValidationError
from odoo.tools.intervals import Intervals
from odoo.tools.intervals import _boundaries


def _naive_utc(dt):
    return dt.astimezone(utc).replace(tzinfo=None)


def _midnight(date):
    return datetime.combine(date, datetime.min.time())


def _replace_interval_records(intervals, records):
    return Intervals((start, end, records) for (start, end, _) in intervals)


def _record_overlap_intervals(intervals):
    boundaries = sorted(_boundaries(intervals, 'start', 'stop'))
    counts = {}
    interval_vals = []
    ids = set()
    start = None
    for (time, flag, records) in boundaries:
        for record in records:
            if (
                new_count := counts.get(record.id, 0) + {'start': 1, 'stop': -1}[flag]
            ):
                counts[record.id] = new_count
            else:
                del counts[record.id]
        new_ids = set(counts.keys())
        if ids != new_ids:
            if ids and start is not None:
                interval_vals.append((start, time, records.browse(ids)))
            if new_ids:
                start = time
        ids = new_ids
    return Intervals(interval_vals, keep_distinct=True)


def _time_delta_hours(td):
    return td.total_seconds() / 3600


def _last_hours_as_intervals(starting_intervals, hours):
    last_hours_intervals = []
    for (start, stop, record) in reversed(starting_intervals):
        duration = _time_delta_hours(stop - start)
        if hours >= duration:
            last_hours_intervals.append((start, stop, record))
            hours -= duration
        elif hours > 0:
            last_hours_intervals.append((stop - relativedelta(hours=hours), stop, record))
            break
        else:
            break
    return Intervals(last_hours_intervals)


class HrAttendanceOvertimeRule(models.Model):
    _name = 'hr.attendance.overtime.rule'
    _description = "Overtime Rule"

    name = fields.Char(required=True)
    description = fields.Html()
    base_off = fields.Selection([
            ('quantity', "Quantity"),
            ('timing', "Timing"),
        ],
        string="Based Off",
        required=True,
        default='quantity',
        help=(
            "Base for overtime calculation.\n"
            "Use 'Quantity' when overtime hours are those in excess of a certain amount per day/week.\n"
            "Use 'Timing' when overtime hours happen on specific days or at specific times"
        ),
    )

    timing_type = fields.Selection([
        ('work_days', "On any working day"),
        ('non_work_days', "On any non-working day"),
        ('leave', "When employee is off"),
        ('schedule', "Outside of a specific schedule"),
        # ('employee', "Outside the employee's working schedule"),
        # ('off_time', "When employee is off"),  # TODO in ..._holidays
        # ('public_leave', "On a holiday"), ......
    ])
    timing_start = fields.Float("From", default=0)
    timing_stop = fields.Float("To", default=24)
    expected_hours_from_contract = fields.Boolean("Hours from employee schedule", default=True)

    resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string="Schedule",
        domain=[('flexible_hours', '=', False)],
    )

    expected_hours = fields.Float(string="Usual work hours")
    quantity_period = fields.Selection([
            ('day', 'Day'),
            ('week', 'Week')
        ],
        default='day',
    )
    sequence = fields.Integer(default=10)

    ruleset_id = fields.Many2one('hr.attendance.overtime.ruleset', required=True, index=True)
    company_id = fields.Many2one(related='ruleset_id.company_id')

    paid = fields.Boolean("Pay Extra Hours")
    amount_rate = fields.Float("Rate", default=1.0)

    employee_tolerance = fields.Float()
    employer_tolerance = fields.Float()

    information_display = fields.Char("Information", compute='_compute_information_display')

    _timing_start_is_hour = models.Constraint(
        'CHECK(0 <= timing_start AND timing_start < 24)',
        "Timing Start is an hour of the day",
    )
    _timing_stop_is_hour = models.Constraint(
        'CHECK(0 <= timing_stop AND timing_stop <= 24)',
        "Timing Stop is an hour of the day",
    )

    # Quantity rule well defined
    @api.constrains('base_off', 'expected_hours', 'quantity_period')
    def _check_expected_hours(self):
        for rule in self:
            if (
                rule.base_off == 'quantity'
                and not rule.expected_hours_from_contract
                and not rule.expected_hours
            ):
                raise ValidationError(self.env._("Rule '%(name)s' is based off quantity, but the usual amount of work hours is not specified", name=rule.name))

            if rule.base_off == 'quantity' and not rule.quantity_period:
                raise ValidationError(self.env._("Rule '%(name)s' is based off quantity, but the period is not specified", name=rule.name))

    # Timing rule well defined
    @api.constrains('base_off', 'timing_type', 'resource_calendar_id')
    def _check_work_schedule(self):
        for rule in self:
            if (
                rule.base_off == 'timing'
                and rule.timing_type == 'schedule'
                and not rule.resource_calendar_id
            ):
                raise ValidationError(self.env._("Rule '%(name)s' is based off timing, but the work schedule is not specified", name=rule.name))

    def _get_local_time_start(self, date, tz):
        self.ensure_one()
        ret = _midnight(date) + relativedelta(hours=self.timing_start)
        return _naive_utc(tz.localize(ret))

    def _get_local_time_stop(self, date, tz):
        self.ensure_one()
        if self.timing_stop == 24:
            ret = datetime.combine(date, datetime.max.time())
            return _naive_utc(tz.localize(ret))
        ret = _midnight(date) + relativedelta(hours=self.timing_stop)
        return _naive_utc(tz.localize(ret))

    def _get1_timing_overtime_intervals(self, attendances, version_map):
        self.ensure_one()
        attendances.employee_id.ensure_one()
        assert self.base_off == 'timing'

        employee = attendances.employee_id
        start_dt = min(attendances.mapped('check_in'))
        end_dt = max(attendances.mapped('check_out'))

        if self.timing_type in ['work_days', 'non_work_days']:
            company = self.company_id or employee.company_id
            unusual_days = company.resource_calendar_id._get_unusual_days(start_dt, end_dt)

            attendance_intervals = []
            for date, day_attendances in attendances.filtered(
                lambda att: unusual_days.get(att.date.strftime('%Y-%m-%d'), None) == (self.timing_type == 'non_work_days')
            ).grouped('date').items():
                tz = timezone(version_map[employee][date]._get_tz())
                time_start = self._get_local_time_start(date, tz)
                time_stop = self._get_local_time_stop(date, tz)

                attendance_intervals.extend([(
                        max(time_start, attendance.check_in),
                        min(time_stop, attendance.check_out),
                        attendance,
                    ) for attendance in day_attendances
                    if time_start <= attendance.check_out and attendance.check_in <= time_stop
                ])

            overtime_intervals = Intervals(attendance_intervals, keep_distinct=True)
        else:
            attendance_intervals = [
                (att.check_in, att.check_out, att)
                for att in attendances
            ]
            resource = attendances.employee_id.resource_id
            # Just use last version for now
            last_version = version_map[employee][max(attendances.mapped('date'))]
            tz = timezone(last_version._get_tz())
            if self.timing_type == 'schedule':
                work_schedule = self.resource_calendar_id
                work_intervals = Intervals()
                for lunch in [False, True]:
                    work_intervals |= Intervals(
                        (_naive_utc(start), _naive_utc(end), records)
                        for (start, end, records)
                        in work_schedule._attendance_intervals_batch(
                            utc.localize(start_dt),
                            utc.localize(end_dt),
                            resource,
                            tz=tz,
                            lunch=lunch,
                        )[resource.id]
                    )
                overtime_intervals = Intervals(attendance_intervals, keep_distinct=True) - work_intervals
            elif self.timing_type == 'leave':
                # TODO: completely untested
                leave_intervals = last_version.resource_calendar_id._leave_intervals_batch(
                    utc.localize(start_dt),
                    utc.localize(end_dt),
                    resource,
                    tz=tz,
                )[resource.id]
                overtime_intervals = Intervals(attendance_intervals, keep_distinct=True) & leave_intervals

        if self.employer_tolerance:
            overtime_intervals = Intervals((
                    ot for ot in overtime_intervals
                    if _time_delta_hours(ot[1] - ot[0]) >= self.employer_tolerance
                ),
                keep_distinct=True,
            )
        return overtime_intervals

    @api.model
    def _get_periods(self):
        return [name for (name, _) in self._fields['quantity_period'].selection]

    @api.model
    def _get_period_keys(self, date):
        return {
            'day': date,
            # use sunday as key for whole week;
            # also determines which version we use for the whole week
            'week': date + relativedelta(days=6 - date.weekday()),
        }

    def _get_expected_hours_from_contract(self, date, version, period='day'):
        # todo : improve performance with batch on mapped versions
        date_start = date
        date_end = date
        if period == 'week':
            date_start = date_start - relativedelta(days=date_start.weekday())  # Set to Monday
            date_end = date_start + relativedelta(days=6)  # Set to Sunday
        date_start = datetime.combine(date_start, datetime.min.time())
        date_end = datetime.combine(date_end, datetime.max.time())
        expected_work_time = version.employee_id._employee_attendance_intervals(
            utc.localize(date_start),
            utc.localize(date_end)
        )
        delta = sum((i[1] - i[0]).total_seconds() for i in expected_work_time)
        expected_hours = delta / 3600.0

        return expected_hours

    def _get_overtime_intervals_by_date(self, attendances, version_map):
        """ return all overtime over the attendances (all of the SAME employee)
            as a list of `Intervals` sets with the rule as the recordset
            generated by `timing` rules in self
        """
        attendances.employee_id.ensure_one()
        employee = attendances.employee_id
        if not attendances:
            return [Intervals(keep_distinct=True)]

        # Timing based
        timing_intervals_by_date = defaultdict(list)
        all_timing_overtime_intervals = Intervals(keep_distinct=True)
        for rule in self.filtered(lambda r: r.base_off == 'timing'):
            new_intervals = rule._get1_timing_overtime_intervals(attendances, version_map)
            all_timing_overtime_intervals |= new_intervals
            for start, end, attendance in new_intervals:
                timing_intervals_by_date[attendance.date].append((start, end, rule))
            # timing_intervals_list.append(
            #     Intervals((start, end, (rule, attendance.date)) for (start, end, attendance) in intervals)
            # )
            # timing_intervals_list.append(
            #     _replace_interval_records(new_intervals, rule)
            # )

        # Quantity Based
        periods = self._get_periods()

        work_hours_by = {period: defaultdict(lambda: 0) for period in periods}
        attendances_by = {period: defaultdict(list) for period in periods}
        overtime_hours_by = {period: defaultdict(lambda: 0) for period in periods}
        overtimes_by = {period: defaultdict(list) for period in periods}
        for attendance in attendances:
            for period, key_date in self._get_period_keys(attendance.date).items():
                work_hours_by[period][key_date] += attendance.worked_hours
                attendances_by[period][key_date].append(
                    (attendance.check_in, attendance.check_out, attendance)
                )
        for start, end, attendance in all_timing_overtime_intervals:
            for period, key_date in self._get_period_keys(attendance.date).items():
                overtime_hours_by[period][key_date] += _time_delta_hours(end - start)
                overtimes_by[period][key_date].append((start, end, attendance))

        # list -> Intervals
        for period in periods:
            overtimes_by[period] = defaultdict(
                lambda: Intervals(keep_distinct=True),
                {
                    date: Intervals(ots, keep_distinct=True)
                    for date, ots in overtimes_by[period].items()
                }
            )
            # non overtime attendances
            attendances_by[period] = defaultdict(
                lambda: Intervals(keep_distinct=True),
                {
                    date: Intervals(atts, keep_distinct=True) - overtimes_by[period][date]
                    for date, atts in attendances_by[period].items()
                }
            )

        quantity_intervals_by_date = defaultdict(list)
        for rule in self.filtered(lambda r: r.base_off == 'quantity').sorted(
            lambda r: {p: i for i, p in enumerate(periods)}[r.quantity_period]
        ):
            period = rule.quantity_period
            for date in attendances_by[period]:
                if rule.expected_hours_from_contract:
                    expected_hours = self._get_expected_hours_from_contract(date, version_map[employee][date], period)
                else:
                    expected_hours = rule.expected_hours

                overtime_quantity = work_hours_by[period][date] - expected_hours
                # if overtime_quantity <= -rule.employee_tolerance and rule.undertime: make negative adjustment
                if overtime_quantity <= 0 or overtime_quantity <= rule.employer_tolerance:
                    continue
                if overtime_quantity < overtime_hours_by[period][date]:
                    for start, end, attendance in _last_hours_as_intervals(
                        starting_intervals=overtimes_by[period][date],
                        hours=overtime_quantity,
                    ):
                        quantity_intervals_by_date[attendance.date].append((start, end, rule))
                else:
                    new_intervals = _last_hours_as_intervals(
                        starting_intervals=attendances_by[period][date],
                        hours=overtime_quantity - overtime_hours_by[period][date],
                    )

                    # Uncommenting this changes the logic of how rules for different periods will interact.
                    # Would make it so weekly overtimes try to overlap daily overtimes as much as possible
                    # for outer_period, key_date in self._get_period_keys(date).items():
                    #     overtimes_by[outer_period][key_date] |= new_intervals
                    #     attendances_by[outer_period][key_date] -= new_intervals
                    #     overtime_hours_by[outer_period][key_date] += sum(
                    #         (end - start).seconds / 3600
                    #         for (start, end, _) in new_intervals
                    #     )

                    for start, end, attendance in (
                        new_intervals | overtimes_by[period][date]
                    ):
                        date = attendance[0].date
                        quantity_intervals_by_date[date].append((start, end, rule))
        intervals_by_date = {}
        for date in quantity_intervals_by_date.keys() | timing_intervals_by_date.keys():
            intervals_by_date[date] = _record_overlap_intervals([
                *timing_intervals_by_date[date],
                *quantity_intervals_by_date[date],
            ])
        return intervals_by_date

    def _generate_overtime_vals(self, employee, attendances, version_map):
        # * Some attendances "see each other"
        #   -- when they happen in the same week for the same employee
        #   -- the overtimes linked to them will depend on surrounding attendances.
        #   this assume ``attendances`` is a self contained subset
        #   (i.e. we ignore all attendances not passed in the argument)
        #   (in pratices the attendances that see each other are found in `_update_overtime`)
        # * version_map[a.employee_id][a.date] is in the map for every attendance a in attendances
        vals = []
        for date, intervals in self._get_overtime_intervals_by_date(attendances, version_map).items():
            vals.extend([
                {
                    'time_start': start,
                    'time_stop': stop,
                    'duration': _time_delta_hours(stop - start),
                    'employee_id': employee.id,
                    'date': date,
                    'rule_ids': rules.ids,
                    **rules._extra_overtime_vals(),
                }
                for start, stop, rules in intervals
            ])
        return vals

    def _extra_overtime_vals(self):
        paid_rules = self.filtered('paid')
        if not paid_rules:
            return {'amount_rate': 0.0}

        max_rate_rule = max(paid_rules, key=lambda r: (r.amount_rate, r.sequence))
        if self.ruleset_id.rate_combination_mode == 'max':
            combined_rate = max_rate_rule.amount_rate
        if self.ruleset_id.rate_combination_mode == 'sum':
            combined_rate = sum((r.amount_rate - 1. for r in paid_rules), start=1.)

        return {
            'amount_rate': combined_rate,
        }

    def _compute_information_display(self):
        timing_types = dict(self._fields['timing_type'].selection)
        for rule in self:
            if rule.base_off == 'quantity':
                if rule.expected_hours_from_contract:
                    rule.information_display = self.env._("From Employee")
                    continue
                rule.information_display = self.env._(
                    "%(nb_hours)d h / %(period)s",
                    nb_hours=rule.expected_hours,
                    period={
                        'day': self.env._('day'),
                        'week': self.env._('week'),
                    }[rule.quantity_period],
                )
            else:
                if rule.timing_type == 'schedule':
                    rule.information_display = self.env._(
                        "Outside Schedule: %(schedule_name)s",
                        schedule_name=rule.resource_calendar_id.name,
                    )
                    continue
                rule.information_display = timing_types[rule.timing_type]
