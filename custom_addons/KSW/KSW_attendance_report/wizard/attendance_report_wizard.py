import pytz
from calendar import monthrange
from datetime import datetime as dt, date, timedelta

from odoo import fields, models


class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'Monthly Attendance Report Wizard'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
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

    def action_print(self):
        """Return the report action."""
        self.ensure_one()
        return self.env.ref(
            'KSW_attendance_report.action_report_monthly_attendance'
        ).report_action(self)

    # ------------------------------------------------------------------
    # Report data computation (called from QWeb template via docs)
    # ------------------------------------------------------------------

    def get_report_data(self):
        """Compute and return all data needed for the PDF template."""
        self.ensure_one()
        employee = self.employee_id.sudo()
        company = employee.company_id or self.env.company
        month = int(self.month)
        year = self.year

        num_days = monthrange(year, month)[1]
        date_from = date(year, month, 1)
        date_to = date(year, month, num_days)

        # -- Fetch attendance records for the month (UTC boundaries) --
        dt_from = dt.combine(date_from, dt.min.time())
        dt_to = dt.combine(date_to + timedelta(days=1), dt.min.time())

        attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', dt_from),
            ('check_in', '<', dt_to),
        ], order='check_in asc')

        # -- Fetch validated leaves overlapping the month --
        leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', dt.combine(date_to, dt.max.time())),
            ('date_to', '>=', dt_from),
        ])

        # -- Build a map: calendar date -> list of attendance records --
        emp_tz = self._get_employee_tz(employee)
        att_by_date = {}
        for att in attendances:
            if att.x_is_absent:
                att_date = att.check_in.date()
            else:
                local_ci = pytz.utc.localize(att.check_in).astimezone(emp_tz)
                att_date = local_ci.date()
            att_by_date.setdefault(att_date, []).append(att)

        # -- Build daily rows --
        month_names = [
            '', 'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December',
        ]
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                     'Friday', 'Saturday', 'Sunday']

        days = []
        totals = {
            'present': 0,
            'absent': 0,
            'leave': 0,
            'weekend': 0,
            'weekend_worked': 0,
            'no_record': 0,
            'worked_hours': 0.0,
            'late_minutes': 0.0,
            'early_leave_minutes': 0.0,
        }

        today = date.today()

        for day_num in range(1, num_days + 1):
            d = date(year, month, day_num)
            day_name = day_names[d.weekday()]
            day_atts = att_by_date.get(d, [])
            leave_name = self._get_leave_name(leaves, d)

            row = {
                'date': d.strftime('%d/%m/%Y'),
                'day': day_name[:3],
                'status': '',
                'status_class': '',
                'check_in': '',
                'check_out': '',
                'worked_hours': 0.0,
                'late_min': 0.0,
                'early_leave_min': 0.0,
                'notes': '',
            }

            if not day_atts:
                if leave_name:
                    row['status'] = 'Leave'
                    row['status_class'] = 'leave'
                    row['notes'] = leave_name
                    totals['leave'] += 1
                elif d > today:
                    row['status'] = '—'
                    row['status_class'] = 'future'
                else:
                    row['status'] = 'No Record'
                    row['status_class'] = 'no_record'
                    totals['no_record'] += 1
            else:
                absent_recs = [a for a in day_atts if a.x_is_absent]
                weekend_recs = [a for a in day_atts if a.x_is_weekend]
                normal_recs = [a for a in day_atts
                               if not a.x_is_absent and not a.x_is_weekend]

                if absent_recs:
                    att = absent_recs[0]
                    if att.x_is_covered or not att.x_net_is_absent:
                        row['status'] = 'Absent (Covered)'
                        row['status_class'] = 'covered'
                        row['notes'] = leave_name or 'Covered by Time Off'
                        totals['leave'] += 1
                    else:
                        row['status'] = 'Absent'
                        row['status_class'] = 'absent'
                        totals['absent'] += 1
                elif weekend_recs:
                    att = weekend_recs[0]
                    if att.x_weekend_granted:
                        row['status'] = 'Weekend (Worked)'
                        row['status_class'] = 'weekend_worked'
                        ci_str, co_str = self._format_times(att, emp_tz)
                        row['check_in'] = ci_str
                        row['check_out'] = co_str
                        row['worked_hours'] = att.worked_hours or 0.0
                        totals['weekend_worked'] += 1
                        totals['worked_hours'] += att.worked_hours or 0.0
                    else:
                        row['status'] = 'Weekend'
                        row['status_class'] = 'weekend'
                        totals['weekend'] += 1
                elif normal_recs:
                    first_att = normal_recs[0]
                    last_att = normal_recs[-1]
                    ci_str, _ = self._format_times(first_att, emp_tz)
                    _, co_str = self._format_times(last_att, emp_tz)
                    total_hours = sum(
                        a.x_net_worked_hours or a.worked_hours or 0.0
                        for a in normal_recs)
                    total_late = sum(
                        a.x_net_late_minutes or 0.0 for a in normal_recs)
                    total_early = sum(
                        a.x_net_early_leave_minutes or 0.0
                        for a in normal_recs)

                    row['status'] = 'Present'
                    row['status_class'] = 'present'
                    row['check_in'] = ci_str
                    row['check_out'] = co_str
                    row['worked_hours'] = total_hours
                    row['late_min'] = total_late
                    row['early_leave_min'] = total_early

                    notes = []
                    if total_late > 0:
                        notes.append('Late')
                    if total_early > 0:
                        notes.append('Early Leave')
                    row['notes'] = ', '.join(notes)

                    totals['present'] += 1
                    totals['worked_hours'] += total_hours
                    totals['late_minutes'] += total_late
                    totals['early_leave_minutes'] += total_early
                else:
                    row['status'] = 'Weekend'
                    row['status_class'] = 'weekend'
                    totals['weekend'] += 1

            days.append(row)

        return {
            'employee': employee,
            'company': company,
            'month_name': month_names[month],
            'year': year,
            'days': days,
            'totals': totals,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_employee_tz(self, employee):
        tz_name = (
            employee.resource_calendar_id.tz
            or employee.tz
            or employee.company_id.resource_calendar_id.tz
            or 'UTC'
        )
        return pytz.timezone(tz_name)

    def _format_times(self, att, emp_tz):
        ci_str = ''
        co_str = ''
        if att.check_in:
            local_ci = pytz.utc.localize(att.check_in).astimezone(emp_tz)
            ci_str = local_ci.strftime('%H:%M')
        if att.check_out:
            local_co = pytz.utc.localize(att.check_out).astimezone(emp_tz)
            co_str = local_co.strftime('%H:%M')
        return ci_str, co_str

    def _get_leave_name(self, leaves, check_date):
        check_start = dt.combine(check_date, dt.min.time())
        check_end = dt.combine(check_date, dt.max.time())
        for leave in leaves:
            if leave.date_from <= check_end and leave.date_to >= check_start:
                return leave.holiday_status_id.name or 'Time Off'
        return ''

