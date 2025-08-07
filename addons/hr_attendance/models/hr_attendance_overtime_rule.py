# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from pytz import timezone, utc

from collections import defaultdict
from datetime import date, datetime
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

def _record_overlap_intervals(interval_sets):
    boundaries = sorted(_boundaries(itertools.chain(*interval_sets), 'start', 'stop'))
    counts = {}
    interval_vals = []
    ids = set()
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
            if ids:
                interval_vals.append((start, time, records.browse(ids)))
            if new_ids:
                start = time
        ids = set(new_ids)
    return Intervals(interval_vals, keep_distinct=True)

def _last_hours_as_intervals(starting_intervals, hours, records=set()):
    last_hours_intervals = []
    for (start, stop, _) in reversed(starting_intervals):
        duration = (stop - start).seconds / 3600
        if hours >= duration:
            last_hours_intervals.append((start, stop, records))
            hours -= duration
        elif hours > 0:
            last_hours_intervals.append((stop - relativedelta(hours=hours), stop, records))
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
        #('employee', "Outside the employee's working schedule"),
        ('schedule', "Outside of a specific schedule"),
    ])
    timing_start = fields.Float("From", required=True, default=0) # TODO hour logic, add constraints...
    timing_stop = fields.Float("To", required=True, default=24)
    expected_hours_from_contract = fields.Boolean("Hours from employee schedule", default=True)

    expected_hours = fields.Float(string="Usual work hours")
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 
        string="Schedule",
        domain=[('flexible_hours', '=', False)],
    )
    calendar_attendance_ids = fields.One2many(related='resource_calendar_id.attendance_ids')

    quantity_period = fields.Selection([
            ('day', 'Day'),
            ('week', 'Week')
        ],
        default='day',
    )
    company_id = fields.Many2one('res.company', "Company", default=lambda self: self.env.company)
    sequence = fields.Integer(default=10)

    ruleset_id = fields.Many2one('hr.attendance.overtime.ruleset')

    paid = fields.Boolean("Pay Extra Hours", default=True)
    amount_rate = fields.Float("Salary Rate", default=1.0)

    # TODO replace with widget?
    quantity_display = fields.Char("Quantity", compute='_compute_quantity_display')
    timing_display = fields.Char("Timing", compute='_compute_timing_display')

    #employee_tolerance = fields.Float() TODO with retenues
    employer_tolerance = fields.Float()

    # timing_start, timing_stop are hours
    # TODO could be SQL
    @api.constrains('timing_start', 'timing_stop')
    def _check_hours(self):
        for rule in self:
            if rule.timing_start and not 0 <= rule.timing_start < 24: 
                raise ValidationError(self.env._("Rule %(name): invalid start hour"))
            if rule.timing_stop and not 0 <= rule.timing_stop <= 24: 
                raise ValidationError(self.env._("Rule %(name): invalid end hour"))

    # Quantity rule well defined
    @api.constrains('base_off', 'expected_hours', 'quantity_period')
    def _check_expected_hours(self):
        for rule in self:
            if (
                rule.base_off == 'quantity' 
                and not rule.expected_hours_from_contract
                and not rule.expected_hours
            ):
                raise ValidationError(self.env._("Rule '%(name)s' is based off quantity, but the usual amount of work hours is not specified"), name=rule.name)

            if rule.base_off == 'quantity' and not rule.quantity_period:
                raise ValidationError(self.env._("Rule '%(name)s' is based off quantity, but the period is not specified"), name=rule.name)

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
            if (
                rule.base_off == 'timing'
                and rule.timing_type in ['work_days', 'non_work_days']
                and (not rule.timing_start or not rule.timing_stop)
            ):
                raise ValidationError(self.env._("Missing start/end times for rule: %(name)s", rule_name=rule.name))

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
            assert self.timing_start and self.timing_stop

            unusual_days = self.company_id.resource_calendar_id._get_unusual_days(start_dt, end_dt)
            
            attendance_intervals = []
            for date, day_attendances in attendances.filtered(
                lambda att: unusual_days[att.date.strftime('%Y-%m-%d')] == (self.timing_type == 'non_work_days')
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
            work_schedule = self.resource_calendar_id
            work_intervals = Intervals()
            # Use last timezone
            tz = timezone(
                version_map[employee][max(attendances.mapped('date'))]._get_tz()
            )
            if self.timing_type == 'schedule':
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

        if self.employer_tolerance:
            overtime_intervals = Intervals((
                    ot for ot in overtime_intervals
                    if (ot[1] - ot[0]).seconds / 3600 >= self.employer_tolerance
                ),
                keep_distinct=True,
            )
        return overtime_intervals
        # NOT really in spec actually but feels needed: TODO remove?
        # if self.timing_type == 'employee':
        #     work_intervals = Intervals()
        #     for version in set(version_map[employee]):
        #         tz = version._get_tz()
        #         version_start = tz.localize(_midnight(version.date_start))
        #         version_end = tz.localize(
        #              datetime.combine(version.date_end, datetime.max.time())
        #         )
        #         work_schedule = version.resource_calendar_id
        #              
        #         for lunch in [False, True]:
        #             work_intervals |= Intervals(
        #                 (_naive_utc(start), _naive_utc(end), records) 
        #                 for (start, end, records) 
        #                 in work_schedule._attendance_intervals_batch(
        #                     max(utc.localize(start_dt), version_start),
        #                     min(utc.localize(end_dt), version_end),
        #                     resource,
        #                     lunch=lunch,
        #                 )[resource.id]
            # TODO: if we want to avoid the last version timezon thing it would look something like this
            # versions = sorted(
            #     set(version_map[employee].values), 
            #     key=lambda v: v.date_version,
            # )
            # tz = timezones(versions[0]._get_tz())
            # first_version_tz = [(versions[0], tz)]
            # for version in versions:
            #     if new_tz := timezone(version._get_tz()) != tz:
            #         tz = new_tz
            #         first_version_tz.append((version, tz))

            # work_schedule = self.resource_calendar_id
            # for i, (version, tz) in enumerate(first_version_tz):
            #     tz = timezone(version._get_tz())
            #     version_start = tz.localize(_midnight(version.date_version))
            #     datetime_min = min(version_start, utc.localize(start_dt))
            #     datetime_max = utc.localize(end_dt)
            #     if i < len(first_version_tz):
            #         next_version, next_tz = first_version_tz[i+1]
            #         version_end = next_tz.localize(_midnight(version.date_version))
            #         datetime_max = max(version_end, datetime_max)

            #     for lunch in [False, True]:
            #         work_intervals |= Intervals(
            #             (_naive_utc(start), _naive_utc(end), records) 
            #             for (start, end, records) 
            #             in work_schedule._attendance_intervals_batch(
            #                 datetime_min,
            #                 datetime_max,
            #                 resource,
            #                 tz=tz,
            #                 lunch=lunch,
            #             )[resource.id]
            #         )


    @api.model
    def _get_periods(self):
        return [name for (name, _) in self._fields['quantity_period'].selection]

    @api.model
    def _get_period_keys(self, date):
        return {
            'day': date,
            # use sunday as key for whole week;
            # also determines which version we use for the whole week
            'week': date + relativedelta(days=6-date.weekday()),
        }

    def _get_overtime_intervals(self, attendances, version_map):
        """ return all overtime over the attendances (all of the SAME employee)
            as a list of `Intervals` sets with the rule as the recordset
            generated by `timing` rules in self
        """
        attendances.employee_id.ensure_one()
        employee = attendances.employee_id
        if not attendances:
            return [Intervals(keep_distinct=True)]

        # Timing based
        timing_intervals_list = []
        all_timing_overtime_intervals = Intervals(keep_distinct=True)
        for rule in self.filtered(lambda r: r.base_off == 'timing'):
            new_intervals = rule._get1_timing_overtime_intervals(attendances, version_map)
            all_timing_overtime_intervals |= new_intervals
            timing_intervals_list.append(
                _replace_interval_records(new_intervals, rule)
            )

        # Quantity Based
        periods = self._get_periods()

        work_hours_by = {period: defaultdict(lambda: 0) for period in periods}
        attendances_by = {period: defaultdict(list) for period in periods}
        overtime_hours_by = {period: defaultdict(lambda: 0) for period in periods}
        overtimes_by = {period: defaultdict(list) for period in periods}
        for attendance in attendances:
            tz = timezone(version_map[employee][attendance.date]._get_tz())
            for period, key_date in self._get_period_keys(attendance.check_in.astimezone(tz).date()).items():
                work_hours_by[period][key_date] += attendance.worked_hours
                attendances_by[period][key_date].append(
                    (attendance.check_in, attendance.check_out, set())
                )
        for start, end, attendance in all_timing_overtime_intervals:
            tz = timezone(version_map[employee][attendance.date]._get_tz())
            for period, key_date in self._get_period_keys(start.astimezone(tz).date()).items():
                overtime_hours_by[period][key_date] += (end - start).seconds / 3600
                overtimes_by[period][key_date].append((start, end, set()))

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

        quantity_intervals_list = []
        for rule in self.filtered(lambda r: r.base_off == 'quantity').sorted(
            lambda r: {p: i for i, p in enumerate(periods)}[r.quantity_period]
        ):
            period = rule.quantity_period
            for date in attendances_by[period]:
                # TODO extract in method _get_employee_expected_hours?
                if rule.expected_hours_from_contract:
                    schedule = version_map[employee][date].resource_calendar_id
                    expected_hours = {
                        'day': schedule.hours_per_day,
                        'week': schedule.hours_per_week,
                    }[period]
                else:
                    expected_hours = rule.expected_hours

                overtime_quantity = work_hours_by[period][date] - expected_hours
                if overtime_quantity <= 0:
                    continue  # TODO handle negative
                elif overtime_quantity <= rule.employer_tolerance:
                    continue
                elif overtime_quantity < overtime_hours_by[period][date]:
                    quantity_intervals_list.append(_last_hours_as_intervals(
                        starting_intervals=overtimes_by[period][date],
                        hours=overtime_quantity,
                        records=rule,
                    ))
                else:
                    new_intervals = _last_hours_as_intervals(
                        starting_intervals=attendances_by[period][date],
                        hours=overtime_quantity-overtime_hours_by[period][date],
                        records=rule,
                    )

                    for outer_period, key_date in self._get_period_keys(date).items():
                        overtimes_by[outer_period][key_date] |= new_intervals
                        attendances_by[outer_period][key_date] -= new_intervals
                        overtime_hours_by[outer_period][key_date] += sum(
                            (end - start).seconds / 3600
                            for (start, end, _) in new_intervals
                        )

                    quantity_intervals_list.append(
                        new_intervals |
                        _replace_interval_records(overtimes_by[period][date], rule)
                    )
        return _record_overlap_intervals([*timing_intervals_list, *quantity_intervals_list])

    def _generate_overtime_vals(self, employee, attendances, version_map):
        # * Some attendances "see each other" 
        #   -- when they happen in the same week for the same employee 
        #   -- the overtimes linked to them will depend on surrounding attendances.
        #   this assume ``attendances`` is a self contained subset
        #   (i.e. we ignore all attendances not passed in the argument)
        #   (in pratices the attendances that see each other are found in `_update_overtime`)
        # * version_map[a.employee_id][a.date] is in the map for every attendance a in attendances
        return [
            {
                'time_start': start,
                'time_stop': stop,
                'duration': (stop - start).seconds / 3600,
                'employee_id': employee.id,
                'date': start.astimezone(timezone(employee.tz)).date(),
                'rule_ids': rules.ids,
                **rules._extra_overtime_vals(),
            } 
            for start, stop, rules in self._get_overtime_intervals(attendances, version_map)
        ]

    def _extra_overtime_vals(self):
        paid_rules = self.filtered('paid')
        if not paid_rules:
            return {'amount_rate': 0.0}

        max_rate_rule = max(paid_rules, key=lambda r: (r.amount_rate, r.sequence))
        if self.ruleset_id.combine_overtime_rates == 'max':
            combined_rate = max_rate_rule.amount_rate
        if self.ruleset_id.combine_overtime_rates == 'sum':
            combined_rate = sum((r.amount_rate-1. for r in paid_rules), start=1.)

        return {
            'amount_rate': combined_rate,
        }

    def _compute_quantity_display(self):
        self.quantity_display = ""
        for rule in self.filtered(lambda r: r.base_off == 'quantity'):
            if rule.expected_hours_from_contract:
                rule.quantity_display = self.env._("From Employee")
                continue
            rule.quantity_display = self.env._(
                "%(nb_hours)d h/%(period)s",
                nb_hours=rule.expected_hours,
                period={
                    'day': self.env._('day'),
                    'week': self.env._('week'),
                }[rule.quantity_period],
            )

    def _compute_timing_display(self):
        self.timing_display = ""
        timing_types = dict(self._fields['timing_type'].selection)
        for rule in self.filtered(lambda r: r.base_off == 'timing'):
            if rule.timing_type == 'schedule':
                rule.timing_display = self.env._(
                     "Outside Schedule: %(schedule_name)s", 
                     schedule_name=rule.resource_calendar_id.name,
                )
                continue
            rule.timing_display = timing_types[rule.timing_type]
