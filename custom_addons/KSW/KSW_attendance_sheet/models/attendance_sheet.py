import logging
import pytz
from calendar import monthrange
from datetime import datetime as dt, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

_logger = logging.getLogger(__name__)


class KswAttendanceSheet(models.Model):
    _name = 'ksw.attendance.sheet'
    _description = 'Monthly Attendance Sheet'
    _order = 'year desc, month desc, employee_id'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        required=True, ondelete='cascade',
        domain="[('x_is_attendance_sheet', '=', True)]",
    )
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True,
       default=lambda self: str(fields.Date.context_today(self).month))
    year = fields.Integer(
        string='Year', required=True,
        default=lambda self: fields.Date.context_today(self).year,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', copy=False)

    manager_id = fields.Many2one(
        'hr.employee', string='Manager',
        related='employee_id.parent_id', store=True,
    )
    department_id = fields.Many2one(
        'hr.department', string='Department',
        related='employee_id.department_id', store=True,
    )
    line_ids = fields.One2many(
        'ksw.attendance.sheet.line', 'sheet_id',
        string='Daily Attendance',
    )

    total_days = fields.Integer(
        string='Total Days', compute='_compute_totals', store=True,
    )
    total_attended = fields.Integer(
        string='Attended', compute='_compute_totals', store=True,
    )
    total_absent = fields.Integer(
        string='Absent', compute='_compute_totals', store=True,
    )
    is_locked = fields.Boolean(
        string='Locked', default=False,
        help='Locked sheets cannot be edited. '
             'Set automatically when the month ends.',
    )

    _unique_employee_month_year = models.Constraint(
        'UNIQUE(employee_id, month, year)',
        'Only one attendance sheet per employee per month is allowed.',
    )

    # ------------------------------------------------------------------
    # Auto-generate lines on creation
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        sheets = super().create(vals_list)
        sheets.action_generate_lines()
        return sheets

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------

    @api.depends('line_ids.is_attended')
    def _compute_totals(self):
        for rec in self:
            all_lines = rec.line_ids
            rec.total_days = len(all_lines)
            rec.total_attended = len(all_lines.filtered('is_attended'))
            rec.total_absent = rec.total_days - rec.total_attended

    def _compute_display_name(self):
        month_names = dict(self._fields['month'].selection)
        for rec in self:
            emp = rec.employee_id.name or ''
            mn = month_names.get(rec.month, '')
            rec.display_name = f"{emp} - {mn} {rec.year}"

    # ------------------------------------------------------------------
    # Schedule helpers
    # ------------------------------------------------------------------

    def _get_employee_tz(self, employee):
        """Return pytz timezone for an employee."""
        # sudo: schedule fields on hr.employee require hr.group_hr_user
        employee = employee.sudo()
        tz_name = (
            employee.resource_calendar_id.tz
            or employee.tz
            or employee.company_id.resource_calendar_id.tz
            or 'UTC'
        )
        return pytz.timezone(tz_name)

    def _get_work_schedule(self, employee, check_date):
        """Get scheduled start/end for *employee* on *check_date*.

        Lookup order:
        1. calendar_group_ids → group lines  (KSW custom schedule)
        2. attendance_ids                    (standard Odoo schedule)
        3. Default Sun-Thu 08:00-17:00       (fallback)

        Returns dict(hour_from, hour_to, break_hours) or None.
        """
        # sudo: main_calendar_id and other schedule fields on hr.employee
        # require hr.group_hr_user; sheet supervisors may not have that group.
        employee = employee.sudo()
        calendar = (
            employee.main_calendar_id
            or employee.resource_calendar_id
            or employee.company_id.resource_calendar_id
        )

        day_of_week = str(check_date.weekday())

        # -- 1. Try calendar_group_ids (KSW custom groups) --
        if calendar and calendar.calendar_group_ids:
            base_domain = Domain([
                ('calendar_group_id', 'in', calendar.calendar_group_ids.ids),
                ('dayofweek', '=', day_of_week),
            ])
            date_domain = Domain.AND([
                Domain.OR([
                    Domain([('start_date', '=', False)]),
                    Domain([('start_date', '<=', check_date)]),
                ]),
                Domain.OR([
                    Domain([('end_date', '=', False)]),
                    Domain([('end_date', '>=', check_date)]),
                ]),
            ])

            all_lines = self.env['resource.calendar.group.line'].search(
                Domain.AND([base_domain, date_domain]),
                order='hour_from asc',
            )
            if all_lines:
                work_lines = all_lines.filtered(
                    lambda l: l.day_period != 'break')
                break_lines = all_lines.filtered(
                    lambda l: l.day_period == 'break')
                if work_lines:
                    return {
                        'hour_from': work_lines[0].hour_from,
                        'hour_to': work_lines[-1].hour_to,
                        'break_hours': sum(
                            l.hour_to - l.hour_from for l in break_lines),
                    }
            # Calendar has groups but this day is not scheduled → not a workday
            return None

        # -- 2. Try standard Odoo attendance_ids --
        if calendar and calendar.attendance_ids:
            att_lines = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == day_of_week)
            if att_lines:
                work_atts = att_lines.filtered(
                    lambda a: a.day_period != 'break')
                break_atts = att_lines.filtered(
                    lambda a: a.day_period == 'break')
                if work_atts:
                    return {
                        'hour_from': work_atts[0].hour_from,
                        'hour_to': work_atts[-1].hour_to,
                        'break_hours': sum(
                            a.hour_to - a.hour_from for a in break_atts),
                    }
            # Calendar has attendance lines but this day is not scheduled
            return None

        # -- 3. Fallback: Sun-Thu 08:00-17:00 (Saudi standard) --
        # Only used when the calendar has NO schedule data at all.
        # weekday(): Mon=0 … Sun=6  →  work days = Sun(6), Mon(0)-Thu(3)
        if check_date.weekday() in (0, 1, 2, 3, 6):
            return {
                'hour_from': 8.0,
                'hour_to': 17.0,
                'break_hours': 1.0,
            }

        return None

    def _is_workday(self, employee, check_date):
        """True when the employee has scheduled work on *check_date*."""
        return self._get_work_schedule(employee, check_date) is not None

    # ------------------------------------------------------------------
    # Attendance sync helpers
    # ------------------------------------------------------------------

    def _build_attendance_vals(self, employee, line_date, schedule):
        """Build check_in/check_out/worked_hours for an attended day."""
        emp_tz = self._get_employee_tz(employee)

        if schedule:
            hf = schedule['hour_from']
            ht = schedule['hour_to']
            brk = schedule.get('break_hours', 0.0)
            sh, sm = int(hf), int((hf % 1) * 60)
            eh, em = int(ht), int((ht % 1) * 60)
            local_ci = emp_tz.localize(dt(
                line_date.year, line_date.month, line_date.day, sh, sm,
            ))
            local_co = emp_tz.localize(dt(
                line_date.year, line_date.month, line_date.day, eh, em,
            ))
            if local_co <= local_ci:
                local_co += timedelta(days=1)
            ci_utc = local_ci.astimezone(pytz.utc).replace(tzinfo=None)
            co_utc = local_co.astimezone(pytz.utc).replace(tzinfo=None)
            worked = (co_utc - ci_utc).total_seconds() / 3600.0 - brk
        else:
            # Fallback: 08:00-17:00, 8 h
            local_ci = emp_tz.localize(dt(
                line_date.year, line_date.month, line_date.day, 8, 0,
            ))
            local_co = emp_tz.localize(dt(
                line_date.year, line_date.month, line_date.day, 17, 0,
            ))
            ci_utc = local_ci.astimezone(pytz.utc).replace(tzinfo=None)
            co_utc = local_co.astimezone(pytz.utc).replace(tzinfo=None)
            worked = 8.0

        return ci_utc, co_utc, max(0.0, worked)

    def _sync_line_attendance(self, lines):
        """Create or delete hr.attendance records to match is_attended.

        Called after lines are generated and whenever is_attended changes.
        """
        HrAttendance = self.env['hr.attendance'].sudo()

        for line in lines:
            employee = line.sheet_id.employee_id

            if line.is_attended and not line.attendance_id:
                # -- Check if a record already exists for this day --
                day_start = dt.combine(line.date, dt.min.time())
                day_end = dt.combine(
                    line.date + timedelta(days=1), dt.min.time(),
                )
                existing = HrAttendance.search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', day_start),
                    ('check_in', '<', day_end),
                ], limit=1)
                if existing:
                    line.sudo().write({'attendance_id': existing.id})
                    continue

                # -- Create attendance record --
                schedule = line.sheet_id._get_work_schedule(
                    employee, line.date)
                ci_utc, co_utc, worked = self._build_attendance_vals(
                    employee, line.date, schedule)

                att = HrAttendance.create({
                    'employee_id': employee.id,
                    'check_in': ci_utc,
                    'check_out': co_utc,
                    'x_is_auto_generated': True,
                })
                att.write({'worked_hours': worked})
                line.sudo().write({'attendance_id': att.id})

            elif not line.is_attended and line.attendance_id:
                # -- Delete auto-generated record --
                if line.attendance_id.x_is_auto_generated:
                    line.attendance_id.sudo().unlink()
                line.sudo().write({'attendance_id': False})

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_generate_lines(self):
        """Create one line per calendar day of the month."""
        for sheet in self:
            if sheet.state == 'confirmed':
                raise UserError('Cannot generate lines for a confirmed sheet.')

            # Delete old lines (cascades to unlink auto-generated attendances
            # via ondelete='set null' + the unlink below).
            old_atts = sheet.line_ids.mapped('attendance_id').filtered(
                'x_is_auto_generated')
            sheet.line_ids.unlink()
            if old_atts.exists():
                old_atts.sudo().unlink()

            m = int(sheet.month)
            y = sheet.year
            num_days = monthrange(y, m)[1]

            vals_list = []
            for day in range(1, num_days + 1):
                d = fields.Date.to_date(f'{y}-{m:02d}-{day:02d}')
                is_wd = self._is_workday(sheet.employee_id, d)
                vals_list.append({
                    'sheet_id': sheet.id,
                    'date': d,
                    'is_workday': is_wd,
                    'is_attended': True,   # ALL days default to attended
                })

            new_lines = self.env['ksw.attendance.sheet.line'].create(vals_list)
            # Immediately create hr.attendance records
            sheet._sync_line_attendance(new_lines)

    def action_mark_all_absent(self):
        """Set every line to absent."""
        for sheet in self:
            if sheet.state == 'confirmed':
                raise UserError('Cannot modify a confirmed sheet.')
            sheet.line_ids.write({'is_attended': False})

    def action_mark_all_present(self):
        """Set every line to present."""
        for sheet in self:
            if sheet.state == 'confirmed':
                raise UserError('Cannot modify a confirmed sheet.')
            sheet.line_ids.write({'is_attended': True})

    def _do_confirm(self):
        """Confirm sheets (internal).

        Called automatically by the monthly cron when the month ends.
        Attendance records already exist from real-time sync.
        """
        for sheet in self:
            if sheet.state == 'confirmed':
                continue
            if not sheet.line_ids:
                _logger.warning(
                    'Sheet %s has no lines, skipping confirmation.',
                    sheet.id,
                )
                continue

            # Final sync to ensure all records are up-to-date
            sheet._sync_line_attendance(sheet.line_ids)
            sheet.write({'state': 'confirmed', 'is_locked': True})

    def action_reset_to_draft(self):
        """Reset to draft and remove generated attendance records."""
        for sheet in self:
            if sheet.state != 'confirmed':
                raise UserError('Only confirmed sheets can be reset.')

            att_records = sheet.line_ids.mapped('attendance_id').filtered(
                'x_is_auto_generated',
            )
            sheet.line_ids.sudo().write({'attendance_id': False})
            if att_records:
                att_records.sudo().unlink()

            sheet.write({'state': 'draft', 'is_locked': False})
            # Re-sync attendance records for currently attended lines
            sheet._sync_line_attendance(sheet.line_ids)

    def action_generate_all_sheets(self):
        """Button wrapper so the list-header button can trigger the cron."""
        self._cron_generate_sheets()

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------

    @api.model
    def _cron_generate_sheets(self):
        """Monthly cron: auto-confirm previous month sheets, then create
        new sheets for the current month.
        """
        today = fields.Date.context_today(self)

        # -- 1. Auto-confirm all draft sheets for previous months --
        draft_sheets = self.search([
            ('state', '=', 'draft'),
        ])
        to_confirm = draft_sheets.filtered(
            lambda s: (s.year < today.year)
            or (s.year == today.year and int(s.month) < today.month)
        )
        if to_confirm:
            _logger.info(
                'Attendance sheet cron: auto-confirming %d past-month sheets.',
                len(to_confirm),
            )
            to_confirm._do_confirm()

        # -- 2. Generate sheets for the current month --
        month = str(today.month)
        year = today.year

        employees = self.env['hr.employee'].search([
            ('x_is_attendance_sheet', '=', True),
        ])
        existing = self.search([
            ('month', '=', month),
            ('year', '=', year),
        ])
        existing_emp_ids = set(existing.mapped('employee_id').ids)

        created = 0
        for emp in employees:
            if emp.id not in existing_emp_ids:
                self.create({
                    'employee_id': emp.id,
                    'month': month,
                    'year': year,
                })
                created += 1

        _logger.info(
            'Attendance sheet cron: created %d sheets for %s/%s',
            created, month, year,
        )




