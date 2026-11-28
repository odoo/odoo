# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time, UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import sum_intervals
from odoo.tools.intervals import Intervals
from odoo.tools.float_utils import float_round


class HrLeave(models.Model):
    _inherit = "hr.leave"

    l10n_in_contains_sandwich_leaves = fields.Boolean()
    l10n_in_sandwich_remaining_balance = fields.Float(compute="_compute_l10n_in_sandwich_remaining_balance")

    @api.depends(
        'number_of_days', 'number_of_hours', 'employee_id', 'work_entry_type_id', 'request_date_from',
        'work_entry_type_id.allows_negative', 'work_entry_type_id.requires_allocation',
        'work_entry_type_id.unit_of_measure', 'l10n_in_contains_sandwich_leaves',
    )
    def _compute_l10n_in_sandwich_remaining_balance(self):
        self.l10n_in_sandwich_remaining_balance = 0
        today = fields.Date.context_today(self)
        for leave in self.filtered(lambda l: l.l10n_in_contains_sandwich_leaves and l.employee_id
                                   and l.work_entry_type_id.requires_allocation
                                   and l.work_entry_type_id.allows_negative):
            # Same balance as hr_holidays' allocation warning: a saved request is already
            # deducted from the balance, so ignore it before deducting the requested amount.
            remaining, _allocated = leave.with_context(ignored_leave_ids=leave._origin.ids)._get_allocation_balance(
                leave.request_date_from or today)[leave]
            is_hour = leave.work_entry_type_id.unit_of_measure == 'hour'
            leave.l10n_in_sandwich_remaining_balance = float_round(
                remaining - (leave.number_of_hours if is_hour else leave.number_of_days), precision_digits=2)

    @api.constrains("work_entry_type_id", "request_date_from", "request_date_to")
    def _l10n_in_check_optional_holiday_request_dates(self):
        leaves_to_check = self.filtered(lambda leave: leave.work_entry_type_id.l10n_in_is_limited_to_optional_days)
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

    def _l10n_in_is_working(self, on_date, public_holiday_dates, resource_calendar):
        return on_date not in public_holiday_dates and resource_calendar._works_on_date(on_date)

    def _l10n_in_count_adjacent_non_working(self, start_date, public_holiday_dates, resource_calendar, reverse=False, include_start=False):
        step = -1 if reverse else 1
        first_day = start_date if include_start else start_date + timedelta(days=step)
        current = first_day
        for _ in range(30):
            if self._l10n_in_is_working(current, public_holiday_dates, resource_calendar):
                break
            current += timedelta(days=step)
        if current == first_day:
            return 0
        date_from, date_to = sorted((first_day, current - timedelta(days=step)))
        return self._l10n_in_count_days_by_sandwich_policy(date_from, date_to, public_holiday_dates)

    def _l10n_in_find_linked_leave(self, start_date, public_holiday_dates, resource_calendar, leaves_by_date, reverse=False):
        step = -1 if reverse else 1
        current_date = start_date
        for _ in range(30):
            current_date += timedelta(days=step)
            if self._l10n_in_is_working(current_date, public_holiday_dates, resource_calendar):
                break
        linked_leaves = leaves_by_date.get(current_date, self.env["hr.leave"])
        if linked_leaves and self._l10n_in_has_working_time_left(current_date, linked_leaves):
            return self.env["hr.leave"]
        return linked_leaves

    def _l10n_in_has_working_time_left(self, day, leaves):
        """ Return whether the employee still works part of ``day`` once ``leaves`` are taken,
            e.g. a lone half day. Only whole days off can be part of a sandwich.
        """
        self.ensure_one()
        resource = self.employee_id.resource_id
        start_dt = self._to_utc(day, 0.0, self.employee_id).replace(tzinfo=UTC)
        end_dt = self._to_utc(day, 24.0, self.employee_id).replace(tzinfo=UTC)
        attendances = self.resource_calendar_id._attendance_intervals_batch(
            start_dt, end_dt, resources_per_tz=resource._get_resources_per_tz(),
        ).get(resource.id, Intervals())
        leave_intervals = Intervals([
            (leave.date_from.replace(tzinfo=UTC), leave.date_to.replace(tzinfo=UTC), self.env["hr.leave"])
            for leave in leaves if leave.date_from and leave.date_to
        ])
        return bool(attendances - leave_intervals)

    def _l10n_in_get_linked_leaves(self, leaves_dates_by_employee, public_holidays_date_by_company):
        linked_before = self.env["hr.leave"]
        linked_after = self.env["hr.leave"]

        for leave in self:
            public_holiday_dates = leave._l10n_in_get_public_holiday_dates(public_holidays_date_by_company)
            leaves_by_date = leaves_dates_by_employee.get(leave.employee_id, {})
            linked_before |= leave._l10n_in_find_linked_leave(
                leave.request_date_from, public_holiday_dates, leave.resource_calendar_id, leaves_by_date, reverse=True
            )
            linked_after |= leave._l10n_in_find_linked_leave(
                leave.request_date_to, public_holiday_dates, leave.resource_calendar_id, leaves_by_date, reverse=False
            )
        return linked_before, linked_after

    def _l10n_in_prepare_sandwich_context(self):
        """
            Build and return a tuple:
                (indian_leaves, leaves_by_employee, public_holidays_by_company_id)
            - Filters Indian, sandwich-enabled leaves.
            - Prepares dicts for sibling employee leaves and company public holidays.
        """
        def _to_local_date(datetime, tz):
            return datetime.replace(tzinfo=UTC).astimezone(ZoneInfo(tz)).date()

        indian_leaves = self.filtered(
            lambda leave: leave.company_id.country_id.code == "IN"
            and leave.work_entry_type_id.l10n_in_is_sandwich_leave
        )
        if not indian_leaves:
            return (indian_leaves, {}, {})

        leaves_dates_by_employee = {}
        self.search([
            ('id', 'not in', self.ids),
            ('employee_id', 'in', self.employee_id.ids),
            ('state', 'not in', ['cancel', 'refuse']),
            ('work_entry_type_id.l10n_in_is_sandwich_leave', '=', True),
        ])._l10n_in_add_leaves_by_date(leaves_dates_by_employee)

        public_holidays_dates_by_company = {}
        for company_id, recs in self.env['resource.calendar.leaves']._read_group(
            domain=[
                ('resource_id', '=', False),
                ('company_id', 'in', indian_leaves.company_id.ids),
            ],
            groupby=['company_id'],
            aggregates=['id:recordset'],
        ):
            company_dates = {}
            tz = company_id.tz or self.env.context.get("tz") or self.env.user.tz or "UTC"
            for holiday in recs:
                local_start = _to_local_date(holiday.date_from, tz)
                local_end = _to_local_date(holiday.date_to, tz)
                for offset in range((local_end - local_start).days + 1):
                    company_dates[local_start + timedelta(days=offset)] = holiday
            public_holidays_dates_by_company[company_id] = company_dates

        return indian_leaves, leaves_dates_by_employee, public_holidays_dates_by_company

    def _l10n_in_add_leaves_by_date(self, leaves_dates_by_employee):
        """ Add the leaves to ``leaves_dates_by_employee``: {employee: {date: leaves}}. """
        for leave in self.filtered(lambda leave: leave.request_date_from and leave.request_date_to):
            leaves_by_date = leaves_dates_by_employee.setdefault(leave.employee_id, {})
            for offset in range((leave.request_date_to - leave.request_date_from).days + 1):
                leave_date = leave.request_date_from + timedelta(days=offset)
                leaves_by_date[leave_date] = leaves_by_date.get(leave_date, self.env["hr.leave"]) | leave

    def _l10n_in_count_days_by_sandwich_policy(self, date_from, date_to, public_holiday_dates):
        self.ensure_one()
        policy = self.work_entry_type_id.l10n_in_sandwich_policy or "full"
        calendar = self.resource_calendar_id

        total_leaves = 0
        current_date = date_from

        while current_date <= date_to:
            is_weekend = not calendar._works_on_date(current_date)
            is_public_holiday = current_date in public_holiday_dates
            if (
                policy == "full"
                or (not is_weekend and not is_public_holiday)
                or (policy == "weekend" and is_weekend)
                or (policy == "public_holiday" and is_public_holiday)
            ):
                total_leaves += 1

            current_date += timedelta(days=1)
        return total_leaves

    def _l10n_in_apply_sandwich_rule(self, leave_days, public_holidays_date_by_company, leaves_dates_by_employee):
        self.ensure_one()
        if not (self.request_date_from and self.request_date_to):
            return 0

        date_from = self.request_date_from
        date_to = self.request_date_to
        public_holiday_dates = self._l10n_in_get_public_holiday_dates(public_holidays_date_by_company)
        # A partial first or last day (e.g. a lone half day) makes no sandwich, unless the other
        # leaves of the employee on that day complete it (e.g. the other half day).
        leaves_by_date = leaves_dates_by_employee.get(self.employee_id, {})
        if any(
            self._l10n_in_has_working_time_left(day, (leaves_by_date.get(day, self.env["hr.leave"]) - self._origin) | self)
            for day in {date_from, date_to}
        ):
            return 0
        is_non_working_from = not self._l10n_in_is_working(date_from, public_holiday_dates, self.resource_calendar_id)
        is_non_working_to = not self._l10n_in_is_working(date_to, public_holiday_dates, self.resource_calendar_id)

        if is_non_working_from and is_non_working_to and not any(
            self._l10n_in_is_working(date_from + timedelta(days=x), public_holiday_dates, self.resource_calendar_id)
            for x in range(1, (date_to - date_from).days)
        ):
            return 0

        total_leaves = self._l10n_in_count_days_by_sandwich_policy(date_from, date_to, public_holiday_dates)
        # Don't charge the part of its working days that other requests take (e.g. the other half day).
        working_days = sum(
            self._l10n_in_is_working(date_from + timedelta(days=x), public_holiday_dates, self.resource_calendar_id)
            for x in range((date_to - date_from).days + 1)
        )
        total_leaves -= max(working_days - leave_days, 0)
        linked_before, linked_after = self._l10n_in_get_linked_leaves(leaves_dates_by_employee, public_holidays_date_by_company)
        linked_before_leave = linked_before[:1]
        linked_after_leave = linked_after[:1]
        # Only expand the current leave when the linked record starts before it.
        has_previous_link = bool(linked_before_leave and linked_before_leave.request_date_from < date_from)
        has_next_link = bool(linked_after_leave and linked_after_leave.request_date_from > date_to)

        if has_previous_link:
            total_leaves += self._l10n_in_count_adjacent_non_working(
                date_from, public_holiday_dates, self.resource_calendar_id, reverse=True
            )
        elif is_non_working_from:
            total_leaves -= self._l10n_in_count_adjacent_non_working(
                date_from, public_holiday_dates, self.resource_calendar_id, include_start=True,
            )

        if has_next_link:
            total_leaves += self._l10n_in_count_adjacent_non_working(
                date_to, public_holiday_dates, self.resource_calendar_id
            )
        elif is_non_working_to:
            total_leaves = total_leaves - self._l10n_in_count_adjacent_non_working(
                date_to, public_holiday_dates, self.resource_calendar_id, reverse=True, include_start=True,
            )
        return total_leaves

    def _get_durations(self, check_work_entry_type=True, resource_calendar=None, additional_domain=None):
        result = super()._get_durations(check_work_entry_type=check_work_entry_type, resource_calendar=resource_calendar, additional_domain=additional_domain)

        indian_leaves, leaves_dates_by_employee, public_holidays_date_by_company = self._l10n_in_prepare_sandwich_context()
        if not indian_leaves:
            return result

        for leave in indian_leaves:
            leave._l10n_in_add_leaves_by_date(leaves_dates_by_employee)
            leave_days, hours = result[leave.id]
            if not leave_days or (
                leave.state in ["validate", "validate1"]
                and not self.env.user.has_group("hr_holidays.group_hr_holidays_user")
            ):
                continue
            updated_days = leave._l10n_in_apply_sandwich_rule(leave_days, public_holidays_date_by_company, leaves_dates_by_employee)
            if updated_days and updated_days != leave_days:
                updated_hours = (updated_days * (hours / leave_days)) if leave_days else hours
                result[leave.id] = (updated_days, updated_hours)
                leave.l10n_in_contains_sandwich_leaves = True
            else:
                leave.l10n_in_contains_sandwich_leaves = False
        return result

    def _l10n_in_get_public_holiday_dates(self, public_holidays_date_by_company):
        if self.work_entry_type_id.include_public_holidays_in_duration:
            return {}
        return public_holidays_date_by_company.get(self.company_id, {})

    def _l10n_in_update_neighbors_duration_after_change(self):
        indian_leaves, leaves_dates_by_employee, public_holidays_dates_by_company = self._l10n_in_prepare_sandwich_context()
        if not indian_leaves:
            return
        if all(state in ['refuse', 'cancel'] for state in self.mapped('state')):
            self.l10n_in_contains_sandwich_leaves = False

        linked_before, linked_after = indian_leaves._l10n_in_get_linked_leaves(
            leaves_dates_by_employee, public_holidays_dates_by_company
        )
        neighbors = linked_before | linked_after
        # The other leaves of the same days (e.g. the other half day) may make a sandwich only with these leaves.
        for leave in indian_leaves:
            leaves_by_date = leaves_dates_by_employee.get(leave.employee_id, {})
            for day in {leave.request_date_from, leave.request_date_to}:
                neighbors |= leaves_by_date.get(day, self.env["hr.leave"])
        neighbors -= self
        if not neighbors:
            return

        if any(state in ['validate', 'validate1'] for state in self.mapped('state')):
            neighbors |= self
        # Recompute neighbor durations with the baseline (non-sandwich) logic.
        base_map = super(HrLeave, neighbors)._get_durations(
            check_work_entry_type=True,
            resource_calendar=None,
        )

        for neighbor in neighbors:
            base_days, base_hours = base_map.get(neighbor.id, (neighbor.number_of_days, neighbor.number_of_hours))
            updated_days = neighbor._l10n_in_apply_sandwich_rule(
                base_days,
                public_holidays_date_by_company=public_holidays_dates_by_company,
                leaves_dates_by_employee=leaves_dates_by_employee,
            )
            if updated_days and updated_days != base_days:
                new_hours = (updated_days * (base_hours / base_days)) if base_days else base_hours
                neighbor.write({
                    'number_of_days': updated_days,
                    'number_of_hours': new_hours,
                    'l10n_in_contains_sandwich_leaves': True,
                })
            else:
                neighbor.write({
                    'number_of_days': base_days,
                    'number_of_hours': base_hours,
                    'l10n_in_contains_sandwich_leaves': False,
                })

    @api.ondelete(at_uninstall=False)
    def _ondelete_refresh_neighbors(self):
        """Pre-delete hook: update neighbors as if these records were already deleted"""
        self._l10n_in_update_neighbors_duration_after_change()

    def action_refuse(self):
        res = super().action_refuse()
        self._l10n_in_update_neighbors_duration_after_change()
        return res

    def action_approve(self, check_state=True):
        res = super().action_approve(check_state)
        self._l10n_in_update_neighbors_duration_after_change()
        return res

    def _action_user_cancel(self, reason):
        res = super()._action_user_cancel(reason)
        self._l10n_in_update_neighbors_duration_after_change()
        return res

    def _get_max_allowed_absence_hours(self, base_max_hours):
        max_hours = super()._get_max_allowed_absence_hours(base_max_hours)
        if self.work_entry_type_id.l10n_in_is_sandwich_leave:
            return max(max_hours, self.number_of_hours)
        return max_hours
