# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import models, fields


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    l10n_in_contains_sandwich_leaves = fields.Boolean()

    def _l10n_in_apply_sandwich_rule(self, leave_days, public_holidays, employee_leaves):
        def is_non_working_day(date):
            return not calendar._works_on_date(date) or date in holiday_dates

        def count_adjacent_non_working_days(start_date, step, include_start=False):
            current = start_date if include_start else start_date + timedelta(days=step)
            count = 0
            while is_non_working_day(current):
                count += 1
                current += timedelta(days=step)
            return count

        def find_linked_leave(start_date, step):
            current = start_date + timedelta(days=step)
            while is_non_working_day(current):
                current += timedelta(days=step)
            return leaves_by_date.get(current)

        self.ensure_one()
        if not (self.request_date_from and self.request_date_to):
            return
        date_from = self.request_date_from
        date_to = self.request_date_to
        calendar = self.resource_calendar_id
        holiday_dates = {
            date
            for holiday in public_holidays
            for date in (
                datetime.date(holiday.date_from) + timedelta(days=x)
                for x in range((datetime.date(holiday.date_to) - datetime.date(holiday.date_from)).days + 1)
            )
        }
        is_non_working_from = is_non_working_day(date_from)
        is_non_working_to = is_non_working_day(date_to)

        if is_non_working_from and is_non_working_to:
            has_working_day_in_between = any(
                not is_non_working_day(date_from + timedelta(days=x))
                for x in range(1, (date_to - date_from).days)
            )
            if not has_working_day_in_between:
                return leave_days

        leaves_by_date = {}
        for leave in employee_leaves:
            current = leave['request_date_from']
            while current <= leave['request_date_to']:
                leaves_by_date[current] = leave
                current += timedelta(days=1)

        linked_before = find_linked_leave(date_from, -1)
        linked_after = find_linked_leave(date_to, 1)

        total_leaves = (date_to - date_from).days + 1 if leave_days else leave_days

        if linked_before:
            total_leaves += count_adjacent_non_working_days(date_from, -1)
        if linked_after:
            total_leaves += count_adjacent_non_working_days(date_to, 1)

        if not linked_before and is_non_working_from:
            total_leaves -= count_adjacent_non_working_days(date_from, 1, include_start=True)
        if not linked_after and is_non_working_to:
            total_leaves -= count_adjacent_non_working_days(date_to, -1, include_start=True)

        return total_leaves

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        result = super()._get_durations(check_leave_type, resource_calendar)
        indian_leaves = self.filtered(lambda c: c.company_id.country_id.code == 'IN')
        if not indian_leaves:
            return result

        public_holidays = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', indian_leaves.company_id.ids),
        ])
        leaves_by_employee = dict(self._read_group(
            domain=[
                ('id', 'not in', self.ids),
                ('employee_id', 'in', self.employee_id.ids),
                ('state', 'not in', ['cancel', 'refuse']),
                ('leave_type_request_unit', 'in', ['day', 'half_day']),
                ('request_unit_half', '=', False),
                ('holiday_status_id', '=', self.holiday_status_id.id),
            ],
            groupby=['employee_id'],
            aggregates=['id:recordset'],
        ))
        for leave in indian_leaves:
            if leave.holiday_status_id.l10n_in_is_sandwich_leave and not leave.request_unit_half:
                leave_days, hours = result[leave.id]
                updated_days = leave._l10n_in_apply_sandwich_rule(leave_days, public_holidays, leaves_by_employee.get(leave.employee_id, []))
                if updated_days != leave_days:
                    result[leave.id] = (updated_days, hours)
                    leave.l10n_in_contains_sandwich_leaves = True
                else:
                    leave.l10n_in_contains_sandwich_leaves = False
            else:
                leave.l10n_in_contains_sandwich_leaves = False
        return result
