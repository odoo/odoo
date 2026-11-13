# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _get_overtime_hours(self, date_start=None, date_stop=None):
        """Return the hours of the overtime time off output by the time rules on attendances
        (``exceed`` rules), overlapping a period.

        :param datetime date_start: naive UTC, no lower bound if not set
        :param datetime date_stop: naive UTC, no upper bound if not set
        :return: ``{employee: hours}``
        :rtype: dict
        """
        domain = [
            ('employee_id', 'in', self.ids),
            ('attendance_id', '!=', False),
            ('time_rule_id.threshold_operator', '=', 'exceed'),
            ('state', '=', 'validate'),
        ]
        if date_start:
            domain.append(('date_to', '>', date_start))
        if date_stop:
            domain.append(('date_from', '<', date_stop))
        return dict(self.env['hr.leave'].sudo()._read_group(
            domain, groupby=['employee_id'], aggregates=['number_of_hours:sum'],
        ))

    def _compute_total_overtime(self):
        """Sum the overtime time off of the attendances, see :meth:`_get_overtime_hours`."""
        overtime_by_employee = self._get_overtime_hours()
        for employee in self:
            employee.total_overtime = overtime_by_employee.get(employee, 0.0)

    def _compute_hours_last_month(self):
        """Compute ``hours_last_month_overtime`` from the overtime time off of the attendances
        overlapping the current month until now."""
        super()._compute_hours_last_month()
        now_utc = fields.Datetime.now().replace(tzinfo=UTC)
        for timezone, employees in self.grouped('tz').items():
            now_tz = now_utc.astimezone(ZoneInfo(timezone or 'UTC'))
            start_tz = now_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            overtime_by_employee = employees._get_overtime_hours(
                start_tz.astimezone(UTC).replace(tzinfo=None),
                now_tz.astimezone(UTC).replace(tzinfo=None),
            )
            for employee in employees:
                employee.hours_last_month_overtime = round(overtime_by_employee.get(employee, 0.0), 2)

    def _get_overtime_today(self):
        """Return the hours of the overtime time off of the attendances of the employee today.

        :rtype: float
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        return self._get_overtime_hours(
            datetime.combine(today, time.min), datetime.combine(today, time.max),
        ).get(self, 0.0)

    def get_attendance_data_by_employee(self, date_start, date_stop):
        """Set ``overtime_hours`` to the overtime time off of the attendances overlapping the
        period."""
        attendance_data = super().get_attendance_data_by_employee(date_start, date_stop)
        for employee, overtime_hours in self._get_overtime_hours(date_start, date_stop).items():
            attendance_data[employee.id]['overtime_hours'] = overtime_hours
        return attendance_data
