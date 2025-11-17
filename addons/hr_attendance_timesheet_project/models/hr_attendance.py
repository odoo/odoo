# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

# Tolerance for timesheet vs attendance hour discrepancies (in hours)
# 15 minutes = 0.25 hours
TIMESHEET_TOLERANCE_HOURS = 0.25


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    timesheet_ids = fields.One2many(
        'account.analytic.line',
        'attendance_id',
        string='Timesheets',
        help="Timesheet entries generated from this attendance"
    )
    active_timesheet_id = fields.Many2one(
        'account.analytic.line',
        string='Active Timesheet',
        help="Currently active timesheet entry (not yet closed)"
    )
    current_project_id = fields.Many2one(
        'project.project',
        string='Current Project',
        compute='_compute_current_project',
        store=False,
        help="Project from the active timesheet"
    )
    total_timesheet_hours = fields.Float(
        string='Total Timesheet Hours',
        compute='_compute_timesheet_hours',
        store=True,
        help="Sum of all timesheet hours for this attendance"
    )
    timesheet_hours_diff = fields.Float(
        string='Hours Difference',
        compute='_compute_timesheet_hours',
        store=True,
        help="Difference between timesheet hours and worked hours (positive = excess, negative = missing)"
    )

    @api.depends('active_timesheet_id', 'active_timesheet_id.project_id')
    def _compute_current_project(self):
        """Get current project from active timesheet"""
        for attendance in self:
            attendance.current_project_id = attendance.active_timesheet_id.project_id if attendance.active_timesheet_id else False

    @api.depends('timesheet_ids.unit_amount', 'worked_hours')
    def _compute_timesheet_hours(self):
        """Calculate total timesheet hours and difference with worked hours"""
        for attendance in self:
            total = sum(attendance.timesheet_ids.mapped('unit_amount'))
            attendance.total_timesheet_hours = total
            if attendance.worked_hours:
                attendance.timesheet_hours_diff = total - attendance.worked_hours
            else:
                attendance.timesheet_hours_diff = 0.0

    @api.model
    def create(self, vals):
        """Override create to automatically start timesheet on check-in"""
        attendance = super().create(vals)

        # Only create timesheet on check-in (check_out is empty)
        if not attendance.check_out:
            attendance._create_initial_timesheet()

        return attendance

    def write(self, vals):
        """Override write to handle check-out, timesheet closing, and validation"""
        # Store old values for validation
        old_values = {}
        if 'check_in' in vals or 'check_out' in vals:
            for attendance in self:
                old_values[attendance.id] = {
                    'check_in': attendance.check_in,
                    'check_out': attendance.check_out,
                }

        # If timesheet_ids are being modified via One2many commands, skip individual
        # timesheet validation to avoid checking intermediate states during batch edits.
        # The attendance-level validation will run after all changes are applied.
        if 'timesheet_ids' in vals:
            result = super(HrAttendance, self.with_context(skip_timesheet_attendance_constraint=True)).write(vals)
        else:
            result = super().write(vals)

        # If check_out is being set, close active timesheets and handle gaps
        if 'check_out' in vals and vals['check_out']:
            for attendance in self:
                if attendance.active_timesheet_id:
                    attendance._close_active_timesheet()
                # Auto-fill any gaps after closing timesheets
                attendance._auto_fill_timesheet_gaps()

        # Validate manual edits to check_in/check_out times
        if ('check_in' in vals or 'check_out' in vals) and old_values:
            for attendance in self:
                # Only validate if attendance was already checked out (manual edit scenario)
                old_val = old_values.get(attendance.id, {})
                if old_val.get('check_out') and attendance.timesheet_ids:
                    attendance._validate_timesheet_hours_on_edit()

        return result

    def _create_initial_timesheet(self):
        """Create initial timesheet entry when checking in"""
        self.ensure_one()

        if not self.employee_id:
            return

        # Get project: last project, or default project
        project = self.employee_id.last_project_id or self._get_default_project()

        if not project:
            raise UserError(_("No default project found. Please configure a default project in Settings."))

        # Create timesheet entry (project is stored on timesheet, not attendance)
        timesheet = self.env['account.analytic.line'].create({
            'employee_id': self.employee_id.id,
            'user_id': self.employee_id.user_id.id if self.employee_id.user_id else self.env.user.id,
            'project_id': project.id,
            'date': self.check_in.date(),
            'name': _('Work on %s') % project.name,
            'unit_amount': 0.0,  # Will be calculated on check-out or project change
            'attendance_id': self.id,
        })

        self.active_timesheet_id = timesheet

        # Remember this project for next time
        self.employee_id.last_project_id = project

    def _close_active_timesheet(self):
        """Close active timesheet by calculating worked hours"""
        self.ensure_one()

        if not self.active_timesheet_id:
            return

        # Calculate hours from timesheet start to now (or check_out)
        end_time = self.check_out or fields.Datetime.now()
        start_time = self.check_in

        # Find when this timesheet started (it might not be at check_in if project was changed)
        timesheet_start = start_time

        # Get all timesheets for this attendance ordered by creation
        all_timesheets = self.timesheet_ids.sorted('create_date')
        if len(all_timesheets) > 1:
            # Find the start time of active timesheet
            # It's either check_in or the end of previous timesheet
            active_index = None
            for idx, ts in enumerate(all_timesheets):
                if ts.id == self.active_timesheet_id.id:
                    active_index = idx
                    break

            if active_index is not None and active_index > 0:
                # Get accumulated hours from previous timesheets
                previous_hours = sum(all_timesheets[:active_index].mapped('unit_amount'))
                # Calculate start time based on previous hours
                from datetime import timedelta
                timesheet_start = start_time + timedelta(hours=previous_hours)

        # Calculate hours
        duration = end_time - timesheet_start
        hours = duration.total_seconds() / 3600.0

        self.active_timesheet_id.write({
            'unit_amount': hours,
        })

        self.active_timesheet_id = False

    def action_change_project(self):
        """Open wizard to change project during work"""
        self.ensure_one()

        if self.check_out:
            raise UserError(_("Cannot change project after check-out."))

        # Get current project from active timesheet
        current_project_id = self.active_timesheet_id.project_id.id if self.active_timesheet_id and self.active_timesheet_id.project_id else False

        return {
            'name': _('Change Project'),
            'type': 'ir.actions.act_window',
            'res_model': 'attendance.change.project.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_attendance_id': self.id,
                'default_current_project_id': current_project_id,
            },
        }

    def change_project_to(self, new_project_id):
        """Change to a new project, closing current timesheet and starting new one"""
        self.ensure_one()

        if self.check_out:
            raise UserError(_("Cannot change project after check-out."))

        new_project = self.env['project.project'].browse(new_project_id)

        if not new_project.allow_timesheets:
            raise UserError(_("Selected project does not allow timesheets."))

        # Close current active timesheet
        if self.active_timesheet_id:
            self._close_active_timesheet()

        # Create new timesheet for new project (project stored on timesheet, not attendance)
        timesheet = self.env['account.analytic.line'].create({
            'employee_id': self.employee_id.id,
            'user_id': self.employee_id.user_id.id if self.employee_id.user_id else self.env.user.id,
            'project_id': new_project.id,
            'date': self.check_in.date(),
            'name': _('Work on %s') % new_project.name,
            'unit_amount': 0.0,
            'attendance_id': self.id,
        })

        self.active_timesheet_id = timesheet

        # Remember this project for next time
        self.employee_id.last_project_id = new_project

    def _get_default_project(self):
        """Get default project '0 - Koszty Stałe'"""
        default_project = self.env.ref('hr_attendance_timesheet_project.project_koszty_stale', raise_if_not_found=False)

        if not default_project:
            # Fallback: find any project named "0 - Koszty Stałe"
            default_project = self.env['project.project'].search([
                ('name', '=', '0 - Koszty Stałe'),
                ('allow_timesheets', '=', True),
            ], limit=1)

        return default_project

    def _auto_fill_timesheet_gaps(self):
        """Auto-fill timesheet gaps at checkout with tolerance handling"""
        self.ensure_one()

        if not self.worked_hours or not self.check_out:
            return

        # Calculate gap (can be negative if timesheets exceed attendance)
        gap_hours = self.worked_hours - self.total_timesheet_hours

        # If gap is within tolerance (±15 minutes), adjust last timesheet
        if abs(gap_hours) <= TIMESHEET_TOLERANCE_HOURS:
            if gap_hours != 0 and self.timesheet_ids:
                # Find the last timesheet and adjust it
                last_timesheet = self.timesheet_ids.sorted('create_date', reverse=True)[0]
                new_amount = last_timesheet.unit_amount + gap_hours
                if new_amount > 0:  # Don't create negative hours
                    last_timesheet.write({'unit_amount': new_amount})
            return

        # If gap is significant (> 15 minutes), create "0 - Koszty Stałe" entry
        if gap_hours > TIMESHEET_TOLERANCE_HOURS:
            default_project = self._get_default_project()
            if not default_project:
                # Show warning but don't block checkout
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Timesheet Gap Detected'),
                        'message': _('Missing %.2f hours of timesheets, but no default project found to auto-fill.') % gap_hours,
                        'type': 'warning',
                        'sticky': False,
                    }
                }

            # Create auto-fill timesheet entry
            self.env['account.analytic.line'].create({
                'employee_id': self.employee_id.id,
                'user_id': self.employee_id.user_id.id if self.employee_id.user_id else self.env.user.id,
                'project_id': default_project.id,
                'date': self.check_in.date(),
                'name': _('Auto-filled unassigned time'),
                'unit_amount': gap_hours,
                'attendance_id': self.id,
            })

            # Show notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Timesheet Auto-Filled'),
                    'message': _('Added %.2f hours to "%s" project for untracked time.') % (gap_hours, default_project.name),
                    'type': 'info',
                    'sticky': False,
                }
            }

    def _validate_timesheet_hours_on_edit(self):
        """Validate timesheet hours when manually editing attendance times

        This validation applies to everyone, including administrators.
        """
        self.ensure_one()

        if not self.worked_hours:
            return

        # Calculate from current timesheet_ids to include pending changes in transaction
        # (e.g., deleted or modified timesheets in the form that haven't been committed yet)
        total_timesheet_hours = sum(self.timesheet_ids.mapped('unit_amount'))
        max_allowed = self.worked_hours + TIMESHEET_TOLERANCE_HOURS

        # Check if timesheets exceed new attendance hours
        if total_timesheet_hours > max_allowed:
            # Block for everyone (no admin bypass)
            raise ValidationError(_(
                "Cannot save attendance changes: Total timesheet hours (%(timesheet)s h) exceed the new worked hours (%(worked)s h) by more than %(tolerance)s minutes.\n\n"
                "Current timesheets total: %(timesheet)s h\n"
                "New worked hours: %(worked)s h\n"
                "Maximum allowed: %(max)s h (with tolerance)\n"
                "Excess: %(excess)s h (%(excess_min)s min)\n\n"
                "To fix this, you must first reduce or delete timesheet entries before changing attendance times.",
                timesheet=round(total_timesheet_hours, 2),
                worked=round(self.worked_hours, 2),
                max=round(max_allowed, 2),
                tolerance=int(TIMESHEET_TOLERANCE_HOURS * 60),
                excess=round(total_timesheet_hours - self.worked_hours, 2),
                excess_min=int((total_timesheet_hours - self.worked_hours) * 60),
            ))
