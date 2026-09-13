from odoo import models
from zoneinfo import ZoneInfo
from odoo.tools.misc import format_date, format_duration
from odoo.tools.float_utils import float_round


class HrLeaveDisplayNameMixin(models.AbstractModel):
    _name = 'hr.leave.display.name.mixin'
    _description = 'Leave Display Name Mixin'

    def _get_leave_duration_display(self, request_unit, number_of_hours, number_of_days):
        """Format duration string based on request unit (hours or days)"""
        if request_unit == 'hour':
            base_duration = format_duration(number_of_hours)
            hours_str, minutes_str = base_duration.split(':')
            hours = int(hours_str)
            minutes = int(minutes_str)
            if minutes > 0:
                return self.env._("%(hours)dh%(minutes)02d", hours=hours, minutes=minutes)
            return self.env._("%(hours)dh", hours=hours)
        days = float_round(number_of_days, precision_digits=2)
        if days < 1:
            return self.env._("%(days)gd", days=days)
        return self.env._("%(days)g days", days=days)

    def _get_leave_display_date(self, date_from_utc, date_to_utc, number_of_days):
        """Format display date range string"""
        display_date = format_date(self.env, date_from_utc) or ""
        if number_of_days > 1 and date_from_utc and date_to_utc:
            display_date += self.env._(
                ' to %(date_to_utc)s',
                date_to_utc=format_date(self.env, date_to_utc) or "",
            )
        return display_date

    def _build_leave_display_name(self, leave_vals):
        """
        Build display name from a dict of leave values.

        Expected keys:
            - tz: str
            - date_from: datetime
            - date_to: datetime
            - name: str
            - employee_name: str
            - work_entry_type_display: str
            - request_unit: str
            - number_of_hours: float
            - number_of_days: float
            - duration_display: str
        """
        user_tz = ZoneInfo(leave_vals['tz'])
        date_from = leave_vals.get('date_from')
        date_to = leave_vals.get('date_to')
        date_from_utc = date_from and date_from.astimezone(user_tz).date()
        date_to_utc = date_to and date_to.astimezone(user_tz).date()

        time_off_type_display = leave_vals.get('work_entry_type_display', '')
        number_of_hours = leave_vals.get('number_of_hours', 0)
        number_of_days = leave_vals.get('number_of_days', 0)
        request_unit = leave_vals.get('request_unit', 'day')
        duration_display = leave_vals.get('duration_display', '')
        employee_name = leave_vals.get('employee_name', '')

        custom_duration = self._get_leave_duration_display(request_unit, number_of_hours, number_of_days)
        display_date = self._get_leave_display_date(date_from_utc, date_to_utc, number_of_days)
        is_hr_user = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        ctx = self.env.context

        if ctx.get('short_name'):
            short_name = leave_vals.get('name') or time_off_type_display or self.env._('Time Off')
            return self.env._("%(name)s: %(duration)s", name=short_name, duration=duration_display)

        hide_employee = (
            not employee_name
            or (ctx.get('hide_employee_name') and 'employee_id' in ctx.get('group_by', []))
        )
        if hide_employee:
            if ctx.get('scale') in ['month', 'quarter'] and number_of_days <= 1:
                return custom_duration
            if is_hr_user:
                return self.env._(
                    "%(work_entry_type)s %(duration)s",
                    work_entry_type=time_off_type_display,
                    duration=custom_duration,
                )
            return self.env._("%(duration)s", duration=duration_display)

        if not time_off_type_display:
            return self.env._(
                "%(person)s: %(duration)s (%(start)s)",
                person=employee_name,
                duration=duration_display,
                start=display_date,
            )

        return self.env._(
            "%(person)s on %(work_entry_type)s: %(duration)s (%(start)s)",
            person=employee_name,
            work_entry_type=time_off_type_display,
            duration=duration_display,
            start=display_date,
        )
