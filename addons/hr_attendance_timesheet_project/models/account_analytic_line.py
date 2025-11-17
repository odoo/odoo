# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Import tolerance constant from hr_attendance extension
from .hr_attendance import TIMESHEET_TOLERANCE_HOURS


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Attendance',
        index=True,
        help="Link to the attendance record that generated this timesheet entry",
        ondelete='cascade',
    )

    def _compute_calendar_display_name(self):
        """Override to include employee name in calendar view for managers"""
        super()._compute_calendar_display_name()
        for line in self:
            if line.calendar_display_name and line.employee_id:
                # Append employee name: "Project (8h) - Employee Name"
                line.calendar_display_name = f"{line.calendar_display_name} - {line.employee_id.name}"

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-set employee_id and user_id from attendance"""
        for vals in vals_list:
            if vals.get('attendance_id') and not vals.get('employee_id'):
                attendance = self.env['hr.attendance'].browse(vals['attendance_id'])
                if attendance.employee_id:
                    vals['employee_id'] = attendance.employee_id.id
                    # Also set user_id from employee
                    if attendance.employee_id.user_id and not vals.get('user_id'):
                        vals['user_id'] = attendance.employee_id.user_id.id
        return super().create(vals_list)

    @api.constrains('employee_id', 'attendance_id')
    def _check_employee_matches_attendance(self):
        """Ensure timesheet employee matches attendance employee"""
        for line in self:
            if line.attendance_id and line.employee_id:
                if line.employee_id != line.attendance_id.employee_id:
                    raise ValidationError(_(
                        "Timesheet employee (%(timesheet_emp)s) must match attendance employee (%(attendance_emp)s).\n\n"
                        "The timesheet is linked to an attendance for %(attendance_emp)s, "
                        "so the timesheet must also be for the same employee.",
                        timesheet_emp=line.employee_id.name,
                        attendance_emp=line.attendance_id.employee_id.name,
                    ))

    @api.onchange('unit_amount')
    def _onchange_unit_amount_check_attendance(self):
        """Provide immediate feedback when changing timesheet hours from attendance view"""
        if self.attendance_id and self.attendance_id.worked_hours and self.unit_amount:
            # Calculate what the total would be with this change
            # Sum other timesheets (excluding current line being edited) + current line's new value
            # This uses attendance.timesheet_ids which includes pending changes in the form
            other_timesheets_total = sum(
                line.unit_amount
                for line in self.attendance_id.timesheet_ids
                if line.id != self.id and line.id  # Exclude current line
            )
            new_total = other_timesheets_total + self.unit_amount
            max_allowed = self.attendance_id.worked_hours + TIMESHEET_TOLERANCE_HOURS

            if new_total > max_allowed:
                excess = new_total - self.attendance_id.worked_hours
                excess_min = int(excess * 60)

                # Block for everyone (no admin bypass)
                return {
                    'warning': {
                        'title': _('Error: Cannot exceed attendance hours'),
                        'message': _(
                            'Total timesheet hours (%(new_total)s h) cannot exceed attendance worked hours (%(worked)s h) by more than 15 minutes.\n\n'
                            'Attendance: %(check_in)s to %(check_out)s\n'
                            'Worked hours: %(worked)s h\n'
                            'Other timesheets: %(other)s h\n'
                            'This entry: %(current)s h\n'
                            'Total: %(new_total)s h\n'
                            'Maximum allowed: %(max)s h\n'
                            'Excess: %(excess)s h (%(excess_min)s min)\n\n'
                            'Please reduce the hours or adjust the attendance check-in/check-out times first.',
                            new_total=round(new_total, 2),
                            worked=round(self.attendance_id.worked_hours, 2),
                            other=round(other_timesheets_total, 2),
                            current=round(self.unit_amount, 2),
                            max=round(max_allowed, 2),
                            excess=round(excess, 2),
                            excess_min=excess_min,
                            check_in=self.attendance_id.check_in,
                            check_out=self.attendance_id.check_out,
                        )
                    }
                }

    @api.constrains('unit_amount', 'attendance_id')
    def _check_timesheet_not_exceed_attendance(self):
        """Prevent timesheet hours from exceeding attendance hours (with tolerance)

        This validation applies to everyone, including administrators.

        Note: This constraint is skipped when timesheets are edited via One2many
        from the attendance form, as it would check intermediate states during
        batch operations. The attendance-level validation handles those cases.
        """
        # Skip validation during One2many batch edits from attendance form
        if self.env.context.get('skip_timesheet_attendance_constraint'):
            return

        for line in self:
            if line.attendance_id and line.attendance_id.worked_hours:
                attendance = line.attendance_id
                # Calculate total timesheet hours for this attendance
                # Use attendance.timesheet_ids which includes pending changes in the current transaction
                # (e.g., when editing an attendance form with multiple timesheet changes at once)
                total_timesheet_hours = sum(attendance.timesheet_ids.mapped('unit_amount'))
                max_allowed = attendance.worked_hours + TIMESHEET_TOLERANCE_HOURS

                if total_timesheet_hours > max_allowed:
                    # Block for everyone (no admin bypass)
                    raise ValidationError(_(
                        "Total timesheet hours (%(timesheet)s h) cannot exceed attendance worked hours (%(attendance)s h) by more than %(tolerance)s minutes.\n\n"
                        "Attendance: %(check_in)s to %(check_out)s\n"
                        "Worked hours: %(attendance)s h\n"
                        "Total timesheets: %(timesheet)s h\n"
                        "Excess: %(excess)s h (%(excess_min)s min)\n\n"
                        "To fix this, you must either:\n"
                        "1. Reduce the timesheet hours, OR\n"
                        "2. Adjust the attendance check-in/check-out times to increase worked hours",
                        timesheet=round(total_timesheet_hours, 2),
                        attendance=round(attendance.worked_hours, 2),
                        tolerance=int(TIMESHEET_TOLERANCE_HOURS * 60),
                        check_in=attendance.check_in,
                        check_out=attendance.check_out,
                        excess=round(total_timesheet_hours - attendance.worked_hours, 2),
                        excess_min=int((total_timesheet_hours - attendance.worked_hours) * 60),
                    ))
