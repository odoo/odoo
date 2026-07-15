from odoo import models
from zoneinfo import ZoneInfo
from odoo.tools.misc import format_date, format_duration


class HrLeaveDisplayNameMixin(models.AbstractModel):
    _name = 'hr.leave.display.name.mixin'
    _description = 'Leave Display Name Mixin'

    def _get_leave_duration_display(self, request_unit, number_of_hours, number_of_days):
        """Format duration string based on request unit (hours or days)"""
        if request_unit == 'hour':
            return format_duration(number_of_hours)
        if number_of_days <= 1:
            return self.env._("%(days)gd", days=number_of_days)
        return self.env._("%(days)g days", days=number_of_days)

    def _get_leave_display_date(self, date_from_utc, date_to_utc, number_of_days):
        """Format display date range string"""
        display_date = format_date(self.env, date_from_utc) or ""
        if number_of_days > 1 and date_from_utc and date_to_utc:
            display_date += self.env._(
                ' to %(date_to_utc)s',
                date_to_utc=format_date(self.env, date_to_utc) or "",
            )
        return display_date

    def _build_leave_display_name(
        self,
        tz,
        leave,
        employee_name,
        work_entry_type_display,
        duration_display,
    ):
        user_tz = ZoneInfo(tz)
        date_from_utc = leave.date_from and leave.date_from.astimezone(user_tz).date()
        date_to_utc = leave.date_to and leave.date_to.astimezone(user_tz).date()

        custom_duration = self._get_leave_duration_display(leave.work_entry_type_request_unit, leave.number_of_hours, leave.number_of_days)
        display_date = self._get_leave_display_date(date_from_utc, date_to_utc, leave.number_of_days)
        is_hr_user = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        ctx = self.env.context

        if ctx.get('short_name'):
            short_name = leave.name or work_entry_type_display or self.env._('Time Off')
            return self.env._("%(name)s: %(duration)s", name=short_name, duration=duration_display)

        hide_employee = (
            not employee_name
            or (ctx.get('hide_employee_name') and 'employee_id' in ctx.get('group_by', []))
        )
        if hide_employee:
            if ctx.get('scale') in ['month', 'quarter'] and leave.number_of_days <= 1:
                return custom_duration
            if is_hr_user:
                return self.env._(
                    "%(work_entry_type)s %(duration)s",
                    work_entry_type=work_entry_type_display,
                    duration=custom_duration,
                )
            return self.env._("%(duration)s", duration=duration_display)

        if not work_entry_type_display:
            return self.env._(
                "%(person)s: %(duration)s (%(start)s)",
                person=employee_name,
                duration=duration_display,
                start=display_date,
            )

        return self.env._(
            "%(person)s on %(work_entry_type)s: %(duration)s (%(start)s)",
            person=employee_name,
            work_entry_type=work_entry_type_display,
            duration=duration_display,
            start=display_date,
        )
