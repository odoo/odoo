# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from datetime import datetime, timedelta, time
from itertools import chain

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import sum_intervals
from odoo.tools.intervals import Intervals


class HrLeave(models.Model):
    _inherit = "hr.leave"

    l10n_in_contains_sandwich_leaves = fields.Boolean()
    linked_sandwich_leave_id = fields.Many2one(
        "hr.leave",
        string="Linked Sandwich Leave",
        help="The leave linked to this one as part of the sandwich rule."
    )
    has_edge_public_leave = fields.Boolean()

    @api.constrains("holiday_status_id", "request_date_from", "request_date_to")
    def _l10n_in_check_optional_holiday_request_dates(self):
        leaves_to_check = self.filtered(lambda leave: leave.holiday_status_id.l10n_in_is_limited_to_optional_days)
        if not leaves_to_check:
            return
        date_from = min(leaves_to_check.mapped("request_date_from"))
        date_to = max(leaves_to_check.mapped("request_date_to"))
        optional_holidays = dict(self.env["l10n.in.hr.leave.optional.holiday"]._read_group(
            domain=[("date", ">=", date_from), ("date", "<=", date_to)],
            groupby=["date:day"],
            aggregates=["__count"],
        ))
        optional_holidays_intervals = Intervals([(
                datetime.combine(date, time.min),
                datetime.combine(date, time.max),
                self.env['l10n.in.hr.leave.optional.holiday']
            )
            for date in optional_holidays
        ])
        invalid_leaves = []
        for leave in leaves_to_check:
            leave_intervals = Intervals([(
                    datetime.combine(leave.request_date_from, time.min),
                    datetime.combine(leave.request_date_to, time.max),
                    self.env['l10n.in.hr.leave.optional.holiday']
                )])
            common_intervals = leave_intervals & optional_holidays_intervals
            if round(sum_intervals(common_intervals), 2) != round(sum_intervals(leave_intervals), 2):
                invalid_leaves.append(leave.display_name)
        if invalid_leaves:
            raise ValidationError(
                self.env._("The following leaves are not on Optional Holidays:\n - %s", "\n - ".join(invalid_leaves))
            )

    @api.depends('date_from', 'date_to', 'resource_calendar_id', 'holiday_status_id.request_unit', 'holiday_status_id.l10n_in_is_sandwich_leave')
    def _compute_duration(self):
        return super()._compute_duration()

    def _l10n_in_apply_sandwich_rule(self, leave_days, public_holidays, employee_leaves):
        def is_non_working_day(date):
            return date in public_holiday_dates or not self.resource_calendar_id._works_on_date(date)

        def count_adjacent_non_working_days(start_date, reverse=False, include_start=False):
            step = -1 if reverse else 1
            current = start_date if include_start else start_date + timedelta(days=step)
            count = 0
            while is_non_working_day(current):
                count += 1
                current += timedelta(days=step)
            return count

        def find_linked_leave(start_date, reverse=False):
            step = -1 if reverse else 1
            current = start_date + timedelta(days=step)
            while is_non_working_day(current):
                current += timedelta(days=step)
            if linked_leave := leaves_by_date.get(current):
                linked_leave.has_edge_public_leave = any(
                    edge in public_holiday_dates
                    for edge in (linked_leave.request_date_from, linked_leave.request_date_to)
                )
            return linked_leave

        self.ensure_one()
        if not (self.request_date_from and self.request_date_to):
            return None
        date_from = self.request_date_from
        date_to = self.request_date_to
        tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        if public_holidays:
            public_holiday_dates = set(chain.from_iterable(
                ((datetime.date(holiday.date_from.astimezone(tz)) + timedelta(days=x))
                for x in range((holiday.date_to - holiday.date_from).days + 1))
                for holiday in public_holidays
            ))
        else:
            public_holiday_dates = set()
        is_non_working_from = is_non_working_day(date_from)
        is_non_working_to = is_non_working_day(date_to)

        if is_non_working_from and is_non_working_to and all(
            is_non_working_day(date_from + timedelta(days=x))
            for x in range(1, (date_to - date_from).days)
        ):
            return leave_days
        leaves_by_date = dict(chain.from_iterable(
            ((leave['request_date_from'] + timedelta(days=i), leave)
             for i in range((leave['request_date_to'] - leave['request_date_from']).days + 1))
            for leave in employee_leaves
        ))

        total_leaves = (date_to - date_from).days + 1
        linked_before = find_linked_leave(date_from, reverse=True)
        if linked_before:
            total_leaves += count_adjacent_non_working_days(date_from, reverse=True)
        elif is_non_working_from:
            total_leaves -= count_adjacent_non_working_days(date_from, include_start=True)

        linked_after = find_linked_leave(date_to)
        if linked_after:
            total_leaves += count_adjacent_non_working_days(date_to)
        elif is_non_working_to:
            total_leaves -= count_adjacent_non_working_days(date_to, reverse=True, include_start=True)

        self.linked_sandwich_leave_id = linked_before or linked_after

        return total_leaves

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        result = super()._get_durations(check_leave_type, resource_calendar)
        indian_leaves = self.filtered(
            lambda leave: leave.company_id.country_id.code == 'IN'
            and leave.holiday_status_id.l10n_in_is_sandwich_leave
            and not leave.request_unit_half
            and not leave.request_unit_hours
        )
        if not indian_leaves:
            return result

        public_holidays_dict = dict(self.env['resource.calendar.leaves']._read_group(
            domain=[
                ('resource_id', '=', False),
                ('company_id', 'in', indian_leaves.company_id.ids),
            ],
            groupby=['company_id'],
            aggregates=['id:recordset'],
        ))
        leaves_by_employee = dict(self._read_group(
            domain=[
                ('id', 'not in', self.ids),
                ('employee_id', 'in', self.employee_id.ids),
                ('state', 'not in', ['cancel', 'refuse']),
                ('request_unit_half', '=', False),
                ('request_unit_hours', '=', False),
                ('holiday_status_id.l10n_in_is_sandwich_leave', '=', True),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))
        for leave in indian_leaves:
            leave_days, hours = result[leave.id]
            updated_days = leave._l10n_in_apply_sandwich_rule(
                leave_days, public_holidays_dict.get(leave.employee_id.company_id), leaves_by_employee.get(leave.employee_id, []))
            if updated_days != leave_days and leave.state not in ['validate', 'validate1']:
                updated_hours = updated_days * (hours / leave_days) if leave_days else hours
                result[leave.id] = (updated_days, updated_hours)
                leave.l10n_in_contains_sandwich_leaves = True
            else:
                leave.l10n_in_contains_sandwich_leaves = False
        return result
