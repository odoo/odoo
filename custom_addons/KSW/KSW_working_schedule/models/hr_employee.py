from datetime import timedelta

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    main_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Main Work Schedule',
        groups='hr.group_hr_user',
        domain="[('is_temp_schedule', '=', False)]",
        help='The main work schedule for the employee, used for attendance analysis',
    )

    temp_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Temporary Work Schedule',
        groups='hr.group_hr_user',
        domain="[('is_temp_schedule', '=', True)]",
        help='The temporary work schedule for the employee, used for attendance analysis',
    )

    # ------------------------------------------------------------------
    # General working-schedule infrastructure:
    # Override _get_calendar_attendances to fall back to
    # resource.calendar.group.line when standard attendance_ids are empty.
    # This bridges calendar_group_ids into the standard Odoo API so that
    # _get_consumed_leaves, _attendance_intervals_batch, and any other
    # internal that relies on resource.calendar.attendance still works
    # correctly for our custom schedule setup.
    # ------------------------------------------------------------------

    def _get_calendar_attendances(self, date_from, date_to):
        """Fall back to calendar_group_ids when attendance_ids is empty."""
        result = super()._get_calendar_attendances(date_from, date_to)

        # If the standard method returned something meaningful, keep it.
        if result.get('days', 0) > 0 or result.get('hours', 0) > 0:
            return result

        # Standard attendance_ids are empty — compute from group lines
        self.ensure_one()
        calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
        if not calendar or not calendar.calendar_group_ids:
            return result

        all_lines = calendar.calendar_group_ids.mapped('line_ids').filtered(
            lambda l: l.day_period != 'break'
        )
        if not all_lines:
            return result

        break_lines = calendar.calendar_group_ids.mapped('line_ids').filtered(
            lambda l: l.day_period == 'break'
        )
        work_weekdays = set(int(d) for d in all_lines.mapped('dayofweek'))

        start = date_from.date() if hasattr(date_from, 'date') else date_from
        end = date_to.date() if hasattr(date_to, 'date') else date_to

        total_days = 0
        total_hours = 0.0
        current = start
        while current <= end:
            if current.weekday() in work_weekdays:
                day_lines = all_lines.filtered(
                    lambda l, d=current: (not l.start_date or l.start_date <= d)
                                         and (not l.end_date or l.end_date >= d)
                                         and l.dayofweek == str(d.weekday())
                )
                if day_lines:
                    day_work = sum(l.hour_to - l.hour_from for l in day_lines)
                    day_break_lines = break_lines.filtered(
                        lambda l, d=current: (not l.start_date or l.start_date <= d)
                                             and (not l.end_date or l.end_date >= d)
                                             and l.dayofweek == str(d.weekday())
                    )
                    day_break = sum(l.hour_to - l.hour_from for l in day_break_lines)
                    total_days += 1
                    total_hours += day_work - day_break
            current += timedelta(days=1)

        return {'days': total_days, 'hours': total_hours}
