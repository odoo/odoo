# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.addons.resource.models.utils import get_collision_new_rucurrency
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import format_time
from odoo.tools.date_utils import float_to_time, parse_iso_date
from odoo.tools.intervals import Intervals
from odoo.tools.misc import format_date, format_duration


class ResourceCalendarAttendance(models.Model):
    _name = 'resource.calendar.attendance'
    _description = "Work Detail"
    _order = 'sequence, date, dayofweek, hour_from'

    hour_from = fields.Float(string='Work from', compute="_compute_hours", store=True, default=0,
        readonly=False, required=True, index=True, precompute=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to = fields.Float(string='Work to', compute="_compute_hours", store=True, default=0,
        readonly=False, required=True, precompute=True)
    # For the hour duration, the compute function is used to compute the value
    # unambiguously, while the duration in days is computed for the default
    # value but can be manually overridden.
    duration_hours = fields.Float(compute='_compute_duration_hours', string='Hours', store=True, readonly=False)
    calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=True, index=True, ondelete='cascade')
    calendar_type = fields.Selection(related='calendar_id.calendar_type', readonly=True)
    duration_based = fields.Boolean(compute='_compute_duration_based', store=True, precompute=True)
    day_period = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('full_day', 'Full Day')], store=True, compute='_compute_day_period')
    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the resource calendar.")

    # Fixed
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, precompute=True,
        compute="_compute_dayofweek", store=True, readonly=False)

    # Variable
    date = fields.Date()
    recurrency = fields.Boolean()
    recurrency_excluded_occurences = fields.Json()
    recurrency_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
    ], default='weeks')
    recurrency_interval = fields.Integer(string="Interval", default=1, help="Number of days or weeks between each occurrence.")
    recurrency_end_type = fields.Selection([
        ('forever', 'Forever'),
        ('times', 'Occurrences'),
        ('date', 'Until'),
    ], default='forever', string="Recurrence End Condition")
    recurrency_count = fields.Integer(string="Number of Repetitions", default=1)
    recurrency_until = fields.Date(string="Recurrence End Date", compute="_compute_recurrency_until", store=True, readonly=False, precompute=True)

    _check_interval = models.Constraint(
        "CHECK(recurrency IS NOT TRUE OR recurrency_interval >= 1)",
        "The recurrency interval should be greater than 0",
    )

    _check_duration_hours = models.Constraint(
        "CHECK(duration_hours > 0 AND duration_hours <= 24)",
        "The attendance should have a duration between 0 and 24 hours",
    )

    _check_count = models.Constraint(
        "CHECK(recurrency IS NOT TRUE OR recurrency_end_type != 'times' OR recurrency_count > 0)",
        "The recurrency count should be greater than 0",
    )

    _check_recurrency_until = models.Constraint(
        "CHECK(recurrency IS NOT TRUE OR recurrency_until >= date)",
        "A recurrency should finish after the first occurence",
    )

    def _format_attendance(self):
        self.ensure_one()
        return {
            'ids': {self.id},
            'period': (timedelta(**{self.recurrency_type: self.recurrency_interval}).days) if self.recurrency else 0,
            'date': self.date,
            'excluded_ocurrences': set(self.recurrency_excluded_occurences or []),
            'until': self.recurrency_until,
            'max_id': self.id,
        }

    def _check_attendance_for_date(self, check_date=None):
        issue = ""
        if sum(self.mapped('duration_hours')) > 24:
            issue = self.env._("Total duration of attendances cannot exceed 24 hours")
        elif len(set(self.mapped('duration_based'))) > 1:
            issue = self.env._("You can't have duration based and time based attendances on the same day")
        elif not self[0].duration_based and len(self) != len(Intervals([(att.hour_from, att.hour_to, att) for att in self], keep_distinct=True)):
            issue = self.env._("Overlap of attendances")
        if not issue:
            return
        if isinstance(check_date, date):
            header = self.env._("Issue on %(date)s:", date=format_date(self.env, check_date))
        elif isinstance(check_date, str):
            header = self.env._("Issue on %(dayofweek)s:", dayofweek=check_date)
        else:
            header = self.env._("Issue:")
        raise UserError(self.env._("%(header)s\n%(issue)s", header=header, issue=issue))

    def _lock_calendars_for_overlap_check(self):
        """Serialize concurrent overlap checks on the same calendar.

        The recurrence-collision detection below relies on search(), which
        cannot see rows written by a concurrent transaction that has not
        committed yet, so two transactions could each pass the check and commit
        a real overlap. Recurrence collisions cannot be expressed as a SQL
        EXCLUDE constraint, so instead we take a per-calendar lock: two
        transactions touching the same calendar can no longer run their checks
        concurrently. The lock is released at COMMIT, so it must be taken before
        the search and outlive it. Calendars are locked in a deterministic order
        to avoid deadlocks when several are involved.
        """
        calendar_ids = sorted(set(self.calendar_id.ids))
        if not calendar_ids:
            return
        self.env.cr.execute(
            "SELECT id FROM resource_calendar WHERE id IN %s ORDER BY id FOR NO KEY UPDATE",
            [tuple(calendar_ids)],
        )

    def _check_attendances_variable_for_calendar(self, ids_to_check):
        # 1. SORT THE ATTENDANCES - the recurring ones become the leaves of the collision tree,
        #    the single-date ones are grouped by their date for the last step
        recurrent_attendance_leaves = []
        ad_hoc_attendances = defaultdict(lambda: self.env['resource.calendar.attendance'])
        for attendance in self:
            if attendance.recurrency:
                recurrent_attendance_leaves.append(attendance._format_attendance())
            else:
                ad_hoc_attendances[attendance.date] |= attendance
        # 2. BUILD THE COLLISION TREE - we compare each recurring attendance with the others.
        #    When two of them overlap, that overlap becomes a new node of the tree, which we
        #    then compare again with the leaves. We keep going level by level until no new
        #    overlap is found (this way overlaps between overlaps are also caught).
        collision_tree = list(recurrent_attendance_leaves)
        current_level_recurrent_attendance_nodes = list(recurrent_attendance_leaves)
        while current_level_recurrent_attendance_nodes:
            # 2a. SAFETY STOP - too many nodes means the calendar is too complicated, we stop
            if len(collision_tree) > 1000:
                raise UserError(self.env._("Too Complex Calendar"))
            next_level_recurrent_attendance_nodes = []
            for node_reccurency in current_level_recurrent_attendance_nodes:
                for leaf_reccurency in recurrent_attendance_leaves:
                    # 2b. compare each pair only once (not A with B and then B with A)
                    if node_reccurency['max_id'] >= leaf_reccurency['max_id']:
                        continue
                    collision = get_collision_new_rucurrency(node_reccurency, leaf_reccurency)
                    if not collision:
                        continue
                    new_period, new_date, new_excluded, new_until = collision
                    new_ids = node_reccurency['ids'] | leaf_reccurency['ids']
                    # 2c. only raise an error if one of the attendances we are saving is part of this overlap
                    if not ids_to_check.isdisjoint(new_ids):
                        attendances = self.browse(new_ids)
                        attendances._check_attendance_for_date(new_date)
                    next_level_recurrent_attendance_nodes.append({
                        'ids': new_ids,
                        'period': new_period,
                        'date': new_date,
                        'excluded_ocurrences': new_excluded,
                        'until': new_until,
                        'max_id': leaf_reccurency['max_id'],
                    })
            collision_tree.extend(next_level_recurrent_attendance_nodes)
            current_level_recurrent_attendance_nodes = list(next_level_recurrent_attendance_nodes)

        # 3. CHECK THE AD-HOCS ATTENDANCES - for each one, go through the collision tree to
        #    find every node that falls on that day, and check all those attendances together
        for attendance_date, attendances in ad_hoc_attendances.items():
            ids_in_conflict = set()
            for node in collision_tree:
                days_diff = (attendance_date - node['date']).days
                if days_diff >= 0 and days_diff % node['period'] == 0:
                    if str(attendance_date) not in node['excluded_ocurrences']:
                        ids_in_conflict.update(node['ids'])
            if ids_in_conflict or attendances:
                attendances_to_validate = attendances | self.browse(ids_in_conflict)
                if len(attendances_to_validate) > 1:
                    attendances_to_validate._check_attendance_for_date(attendance_date)

    def _check_attendances_fixed_for_calendar(self, ids_to_check):
        dayofweek_labels = dict(self._fields['dayofweek'].get_description(self.env)['selection'])
        for dayofweek, attendances in self.grouped('dayofweek').items():
            if ids_to_check.isdisjoint(attendances.ids):
                continue
            formated_date = dayofweek_labels[dayofweek]
            if len(attendances) > 1:
                attendances._check_attendance_for_date(formated_date)

    @api.constrains('hour_from', 'hour_to', 'duration_hours', 'duration_based', 'date', 'dayofweek',
                    'recurrency', 'recurrency_interval', 'recurrency_type', 'recurrency_until', 'recurrency_excluded_occurences')
    def _check_attendances(self):
        """Will apply the good check behavior depending on the calendar_type of each calendar"""
        # 1. LOCK THE CALENDARS - so two transactions cannot save an overlap on the same calendar at the same time
        self._lock_calendars_for_overlap_check()
        domain = Domain.FALSE
        # 2. BUILD THE SEARCH DOMAIN - for each calendar, look for every attendance that could overlap
        #    with the ones we are saving (so we can check them all together later)
        for calendar, attendances in self.grouped('calendar_id').items():
            if calendar.calendar_type == "variable":
                # for a variable calendar we want:
                # - every single-date attendance (ad-hocs) on the same dates
                # - every recurring attendance still active inside the dates we check
                all_dates = attendances.mapped('date')
                min_date = min(all_dates)
                max_date_list = all_dates + [a.recurrency_until for a in attendances if a.recurrency]
                max_date = max(max_date_list)
                domain |= Domain.AND([
                    Domain('calendar_id', '=', calendar.id),
                    Domain.OR([
                        Domain.AND([
                            Domain('recurrency', '=', True),
                            Domain('date', '<=', max_date),
                            Domain.OR([
                                Domain('recurrency_until', '=', False),
                                Domain('recurrency_until', '>=', min_date),
                            ]),
                        ]),
                        Domain.AND([
                            Domain('recurrency', '=', False),
                            Domain('date', '>=', min_date),
                            Domain('date', '<=', max_date),
                        ]),
                    ]),
                ])
            else:
                # for a fixed calendar we want every attendance on the same day of the week
                domain |= Domain.AND([
                    Domain('calendar_id', '=', calendar.id),
                    Domain('dayofweek', 'in', attendances.mapped('dayofweek')),
                    Domain('date', '=', False),
                ])
        # 3. FETCH THE ATTENDANCES - grouped by calendar, then run the right check on each group
        attendances_by_calendar = self.env['resource.calendar.attendance']._read_group(
            domain,
            groupby=['calendar_id'],
            aggregates=["id:recordset"],
        )
        ids_to_check = set(self.ids)
        for calendar, attendances in attendances_by_calendar:
            if calendar.calendar_type == "variable":
                attendances._check_attendances_variable_for_calendar(ids_to_check)
            else:
                attendances._check_attendances_fixed_for_calendar(ids_to_check)

    @api.constrains('date', 'recurrency_excluded_occurences')
    def _check_prevent_date_on_excluded_occurences(self):
        for attendance in self:
            if attendance.date and fields.Date.to_string(attendance.date) in (attendance.recurrency_excluded_occurences or []):
                raise UserError(self.env._("This date is excluded of the recurrency, to start a new one on this date you should create it from scratch"))

    @api.onchange('hour_from')
    def _onchange_hour_from(self):
        # avoid negative or after midnight
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)

    @api.onchange('hour_to')
    def _onchange_hour_to(self):
        # avoid negative or after midnight
        self.hour_to = min(self.hour_to, 24)
        self.hour_to = max(self.hour_to, 0.0)

        if self.hour_from and not self.hour_to:
            self.hour_from = 0.0

        # avoid wrong order
        self.hour_to = max(self.hour_to, self.hour_from)

    @api.onchange('duration_hours')
    def _onchange_duration_hours(self):
        self.duration_hours = min(self.duration_hours, 24)
        if self.hour_from or self.hour_to:
            if self.hour_from + self.duration_hours > 24:
                self.hour_from = 24 - self.duration_hours
                self.hour_to = 24
            else:
                self.hour_to = self.hour_from + self.duration_hours

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_based(self):
        for attendance in self:
            attendance.duration_based = not attendance.hour_from and not attendance.hour_to

    @api.depends('duration_hours', 'hour_from', 'hour_to', 'calendar_id.hours_per_day')
    def _compute_day_period(self):
        for attendance in self:
            if attendance.duration_hours > (0.75 * attendance.calendar_id.hours_per_day) or attendance.duration_based:
                attendance.day_period = 'full_day'
            elif attendance.hour_from and attendance.hour_to:
                if attendance.hour_from > 12 or (12 - attendance.hour_from <= attendance.hour_to - 12):
                    attendance.day_period = 'afternoon'
                else:
                    attendance.day_period = 'morning'
            else:
                attendance.day_period = 'morning'

    @api.depends('date')
    def _compute_dayofweek(self):
        for attendance in self:
            if attendance.date:
                attendance.dayofweek = str(attendance.date.weekday())
            elif not attendance.dayofweek:  # default value
                attendance.dayofweek = '0'

    @api.depends('hour_from', 'hour_to', 'duration_based')
    def _compute_duration_hours(self):
        for attendance in self:
            if not attendance.duration_based:
                attendance.duration_hours = max(0, attendance.hour_to - attendance.hour_from)

    @api.depends('duration_based')
    def _compute_hours(self):
        for attendance in self:
            if attendance.duration_based:
                attendance.hour_from = attendance.hour_to = 0

    @api.depends('recurrency', 'recurrency_end_type', 'recurrency_type', 'recurrency_interval', 'recurrency_count', 'date')
    def _compute_recurrency_until(self):
        for attendance in self:
            if not attendance.recurrency:
                attendance.recurrency_until = attendance.date
                continue
            match attendance.recurrency_end_type:
                case 'date' if attendance.recurrency_until == date.max:
                    attendance.recurrency_until = date.today()
                case 'times' if attendance.date and attendance.recurrency_type and attendance.recurrency_interval and attendance.recurrency_count:
                    attendance.recurrency_until = attendance.date + timedelta(**{attendance.recurrency_type: attendance.recurrency_interval * (attendance.recurrency_count - 1)})
                case 'forever':
                    attendance.recurrency_until = date.max

    def _compute_display_name(self):
        for attendance in self:
            duration = format_duration(attendance.duration_hours)
            if attendance.duration_based:
                attendance.display_name = self.env._("%(duration)s hours A", duration=duration)
            else:
                attendance.display_name = self.env._("%(hour_from)s - %(hour_to)s (%(duration)s) A",
                                                     hour_from=format_time(self.env, float_to_time(attendance.hour_from), time_format="short"),
                                                     hour_to=format_time(self.env, float_to_time(attendance.hour_to), time_format="short"),
                                                     duration=duration)

    @classmethod
    def _to_dict_fields(cls):
        return [
            'date',
            'dayofweek',
            'day_period',
            'duration_hours',
            'hour_from',
            'hour_to',
            'sequence',
        ]

    def _to_dict(self):
        return self.read(self._to_dict_fields(), load=None)

    def _is_work_period(self):
        self.ensure_one()
        return True

    def _filter_by_date(self, date: date, additional_filter=None):
        """
        Get the attendances for a specific date. For variable schedule, it will return the attendances with the same date or with a recurrency rule matching the date. For fixed schedule, it will return the attendances with the same day of week as the date.

        :param date
        :param additional_filter: optional callable to apply extra filtering in the same loop
        """
        if additional_filter is not None:
            assert callable(additional_filter)
        date_string = fields.Date.to_string(date)

        def date_filter(a):
            if additional_filter and not additional_filter(a):
                return False
            if a.recurrency:
                return a.recurrency_interval and (
                    date_string not in (a.recurrency_excluded_occurences or []) and a.date <= date <= a.recurrency_until
                    and (
                        (a.recurrency_type == 'days' and not (date - a.date).days % a.recurrency_interval)
                        or (a.recurrency_type == 'weeks' and not (date - a.date).days % 7 and not ((date - a.date).days // 7) % a.recurrency_interval)
                    )
                )
            return a.date == date if a.date else a.dayofweek == str(date.weekday())
        return self.filtered(date_filter)

    def _filter_between_dates(self, date_from, date_to):
        def _is_between_dates(att):
            att.ensure_one()
            if att.date:
                if att.recurrency:
                    return att.date <= date_to and att.recurrency_until >= date_from
                return date_from <= att.date <= date_to
            return not att.date

        return self.filtered(_is_between_dates)

    def exclude_occurence(self, date):
        self.ensure_one()
        if (parsed_date := parse_iso_date(date)) == self.date:
            new_date = parsed_date
            excluded = [fields.Date.to_string(self.date), *(self.recurrency_excluded_occurences or [])]
            while new_date <= self.recurrency_until and fields.Date.to_string(new_date) in excluded:
                new_date += timedelta(**{self.recurrency_type: self.recurrency_interval})
            if new_date <= self.recurrency_until:
                if self.recurrency_end_type == 'times':
                    self.recurrency_end_type = 'date'
                self.date = new_date
            else:
                self.unlink()
                return
        excluded_ocurrences = self.recurrency_excluded_occurences or []
        if date not in excluded_ocurrences:
            excluded_ocurrences.append(date)
            self.recurrency_excluded_occurences = excluded_ocurrences

    def exclude_multiple_occurences(self, dates):
        for attendance in self:
            for date_to_exclude in dates:
                attendance.exclude_occurence(date_to_exclude)
                if not attendance.exists():
                    break

    def stop_recurrency(self, date):
        self.ensure_one()
        self.update({
            'recurrency_until': parse_iso_date(date) - relativedelta(days=1),
            'recurrency_end_type': 'date',
        })

    def create_ad_hoc(self, date, changes):
        self.ensure_one()
        data = self.copy_data()[0]
        self.exclude_occurence(date)
        new_data = {
            **data,
            **changes,
        }
        new_data_without_recurrency = {f: v for f, v in new_data.items() if "recurrency" not in f}
        return self.create(new_data_without_recurrency)

    def create_new_recurrency(self, date, changes):
        self.ensure_one()
        data = self.copy_data()[0]
        self.stop_recurrency(date)
        new_data = {
            **data,
            **changes,
        }
        if ('recurrency_end_type' in new_data and 'recurrency_until' in new_data
            and (new_data['recurrency_end_type'] != 'date' or not new_data['recurrency_until'])):
            del new_data['recurrency_until']
        return self.create(new_data)
