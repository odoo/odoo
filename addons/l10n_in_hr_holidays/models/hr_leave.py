# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from datetime import datetime, timedelta

from odoo import api, fields, models


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    l10n_in_contains_sandwich_leaves = fields.Boolean()

    def _l10n_in_is_working(self, on_date, public_holiday_dates, resource_calendar):
        return on_date not in public_holiday_dates and resource_calendar._works_on_date(on_date)

    def _l10n_in_count_adjacent_non_working(self, start_date, public_holiday_dates, resource_calendar, reverse=False, include_start=False):
        step = -1 if reverse else 1
        current = start_date if include_start else start_date + timedelta(days=step)
        count = 0
        while not self._l10n_in_is_working(current, public_holiday_dates, resource_calendar) and count < 30:
            count += 1
            current += timedelta(days=step)
        return count

    def _l10n_in_find_linked_leave(self, start_date, public_holiday_dates, resource_calendar, leaves_by_date, reverse=False):
        step = -1 if reverse else 1
        current_date = start_date
        for _ in range(30):
            current_date += timedelta(days=step)
            if self._l10n_in_is_working(current_date, public_holiday_dates, resource_calendar):
                break
        linked_leave = leaves_by_date.get(current_date, self.env["hr.leave"])
        if linked_leave and (linked_leave.request_unit_half or linked_leave.request_unit_hours):
            return self.env["hr.leave"]
        return linked_leave

    def _l10n_in_get_linked_leaves(self, leaves_dates_by_employee, public_holidays_date_by_company):
        linked_before = self.env["hr.leave"]
        linked_after = self.env["hr.leave"]

        for leave in self:
            public_holiday_dates = public_holidays_date_by_company.get(leave.company_id, {})
            leaves_by_date = leaves_dates_by_employee.get(leave.employee_id, {})
            linked_before |= self._l10n_in_find_linked_leave(
                leave.request_date_from, public_holiday_dates, leave.resource_calendar_id, leaves_by_date, reverse=True
            )
            linked_after |= self._l10n_in_find_linked_leave(
                leave.request_date_to, public_holiday_dates, leave.resource_calendar_id, leaves_by_date, reverse=False
            )
        return linked_before, linked_after

    def _l10n_in_prepare_sandwich_context(self):
        """
            Build and return a tuple:
                (indian_leaves, leaves_by_employee, public_holidays_by_company_id)
            - Filters Indian, full-day, sandwich-enabled leaves.
            - Prepares dicts for sibling employee leaves and company public holidays.
        """
        indian_leaves = self.filtered(
            lambda leave: leave.company_id.country_id.code == "IN"
            and leave.holiday_status_id.l10n_in_is_sandwich_leave
            and not leave.request_unit_half
            and not leave.request_unit_hours
        )
        if not indian_leaves:
            return (indian_leaves, {}, {})

        leaves_dates_by_employee = {
            emp_id: {
                (leave.request_date_from + timedelta(days=offset)): leave
                for leave in recs
                for offset in range((leave.request_date_to - leave.request_date_from).days + 1)
            }
            for emp_id, recs in self._read_group(
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
            )
        }

        tz = pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")
        public_holidays_dates_by_company = {
            company_id: {
                (datetime.date(holiday.date_from.astimezone(tz)) + timedelta(days=offset)): holiday
                for holiday in recs
                for offset in range((holiday.date_to.date() - holiday.date_from.date()).days + 1)
            }
            for company_id, recs in self.env['resource.calendar.leaves']._read_group(
                domain=[
                    ('resource_id', '=', False),
                    ('company_id', 'in', indian_leaves.company_id.ids),
                ],
                groupby=['company_id'],
                aggregates=['id:recordset'],
            )
        }

        return indian_leaves, leaves_dates_by_employee, public_holidays_dates_by_company

    def _l10n_in_apply_sandwich_rule(self, public_holidays_date_by_company, leaves_dates_by_employee):
        self.ensure_one()
        if not (self.request_date_from and self.request_date_to):
            return 0

        date_from = self.request_date_from
        date_to = self.request_date_to
        public_holiday_dates = public_holidays_date_by_company.get(self.company_id, {})
        is_non_working_from = not self._l10n_in_is_working(date_from, public_holiday_dates, self.resource_calendar_id)
        is_non_working_to = not self._l10n_in_is_working(date_to, public_holiday_dates, self.resource_calendar_id)

        if is_non_working_from and is_non_working_to and not any(
            self._l10n_in_is_working(date_from + timedelta(days=x), public_holiday_dates, self.resource_calendar_id)
            for x in range(1, (date_to - date_from).days)
        ):
            return 0

        total_leaves = (date_to - date_from).days + 1
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

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        result = super()._get_durations(check_leave_type, resource_calendar)

        indian_leaves, leaves_dates_by_employee, public_holidays_date_by_company = self._l10n_in_prepare_sandwich_context()
        if not indian_leaves:
            self.l10n_in_contains_sandwich_leaves = False
            return result

        for leave in indian_leaves:
            leave_days, hours = result[leave.id]
            if not leave_days or (
                leave.state in ["validate", "validate1"]
                and not self.env.user.has_group("hr_holidays.group_hr_holidays_user")
            ):
                continue
            updated_days = leave._l10n_in_apply_sandwich_rule(public_holidays_date_by_company, leaves_dates_by_employee)
            if updated_days and updated_days != leave_days:
                updated_hours = (updated_days * (hours / leave_days)) if leave_days else hours
                result[leave.id] = (updated_days, updated_hours)
                leave.l10n_in_contains_sandwich_leaves = True
            else:
                leave.l10n_in_contains_sandwich_leaves = False
        return result

    def _l10n_in_update_neighbors_duration_after_change(self):
        indian_leaves, leaves_dates_by_employee, public_holidays_dates_by_company = self._l10n_in_prepare_sandwich_context()
        if not indian_leaves:
            return
        self.l10n_in_contains_sandwich_leaves = False

        linked_before, linked_after = indian_leaves._l10n_in_get_linked_leaves(
            leaves_dates_by_employee, public_holidays_dates_by_company
        )
        neighbors = (linked_before | linked_after) - self
        if not neighbors:
            return

        # Recompute neighbor durations with the baseline (non-sandwich) logic.
        base_map = super(HolidaysRequest, neighbors)._get_durations(
            check_leave_type=True,
            resource_calendar=None,
        )

        for neighbor in neighbors:
            base_days, base_hours = base_map.get(neighbor.id, (neighbor.number_of_days, neighbor.number_of_hours))
            updated_days = neighbor._l10n_in_apply_sandwich_rule(
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

    def _action_user_cancel(self, reason):
        res = super()._action_user_cancel(reason)
        self._l10n_in_update_neighbors_duration_after_change()
        return res
