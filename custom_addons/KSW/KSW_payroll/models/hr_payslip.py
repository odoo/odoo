from datetime import datetime, time

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

DAILY_HOURS = 8.0
DAYS_PER_MONTH = 30.0


# ======================================================================
# Extend worked-day line — integer display + deduction amount
# ======================================================================

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    number_of_days = fields.Float(digits=(16, 0))
    number_of_hours = fields.Float(digits=(16, 0))
    amount = fields.Float(
        string='Amount',
        digits=(16, 0),
        help='Monetary amount associated with this worked-day entry '
             '(e.g. total attendance deduction).',
    )


# ======================================================================
# Payslip lines — integer display
# ======================================================================

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    amount = fields.Float(digits=(16, 0))
    quantity = fields.Float(digits=(16, 0))
    total = fields.Float(digits=(16, 0))


# ======================================================================
# Payslip: worked-day population + vacation-return guard
# ======================================================================

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # ------------------------------------------------------------------
    # compute_sheet override
    # ------------------------------------------------------------------

    def compute_sheet(self):
        """Guard against unresolved vacations and ensure worked-day lines
        are populated (important for batch-generated payslips where the
        UI onchange never fires)."""
        for payslip in self:
            self._check_unresolved_vacation(payslip)
            if not payslip.worked_days_line_ids:
                self._ensure_worked_days(payslip)
        return super().compute_sheet()

    # ------------------------------------------------------------------
    # Vacation-return guard
    # ------------------------------------------------------------------

    @staticmethod
    def _check_unresolved_vacation(payslip):
        """Raise if the employee has an approved annual leave whose return
        has not yet been HR-confirmed and that started on or before the
        payslip end date."""
        if not payslip.employee_id or not payslip.date_to:
            return
        unresolved = payslip.env['hr.leave'].sudo().search([
            ('employee_id', '=', payslip.employee_id.id),
            ('state', '=', 'validate'),
            ('holiday_status_id.is_annual_leave', '=', True),
            ('x_return_state', 'in', ('on_vacation', 'manager_confirmed')),
            ('request_date_from', '<=', payslip.date_to),
        ])
        if unresolved:
            details = '\n'.join(
                '  • %s (%s → %s)' % (
                    l.holiday_status_id.name,
                    l.request_date_from,
                    l.request_date_to,
                )
                for l in unresolved
            )
            raise ValidationError(_(
                "Cannot compute payslip for %(employee)s.\n\n"
                "The following annual leave(s) have not been fully "
                "confirmed (HR return confirmation is still pending):\n"
                "%(details)s\n\n"
                "Please resolve the vacation return before processing "
                "payroll.",
                employee=payslip.employee_id.name,
                details=details,
            ))

    # ------------------------------------------------------------------
    # Ensure worked-day lines exist (batch / programmatic creation)
    # ------------------------------------------------------------------

    def _ensure_worked_days(self, payslip):
        """Populate worked_days_line_ids when they are empty (e.g. batch
        payslip generation where the UI onchange never fires)."""
        version_ids = (
            payslip.version_id.ids
            or self.get_versions(
                payslip.employee_id, payslip.date_from, payslip.date_to)
        )
        if not version_ids:
            return
        versions = self.env['hr.version'].browse(version_ids)
        wd_vals = self.get_worked_day_lines(
            versions, payslip.date_from, payslip.date_to)
        if wd_vals:
            payslip.worked_days_line_ids = [
                (0, 0, v) for v in wd_vals
            ]

    # ------------------------------------------------------------------
    # get_worked_day_lines — main override
    # ------------------------------------------------------------------

    @api.model
    def get_worked_day_lines(self, versions, date_from, date_to):
        """Build worked-day lines from actual hr.attendance records.

        * Attendance-sheet employees  → attended / absent days only.
        * Biometric employees         → attended, absent, late, early,
                                        plus monetary deduction total.
        * Employees with no attendance data → fall back to the standard
          calendar-based computation from om_hr_payroll.
        """
        res = []
        d_from = (
            fields.Date.to_date(date_from) if isinstance(date_from, str)
            else date_from
        )
        d_to = (
            fields.Date.to_date(date_to) if isinstance(date_to, str)
            else date_to
        )

        for version in versions:
            employee = version.employee_id
            if not employee:
                continue

            # Effective period for this version within the payslip dates
            ver_start = version.contract_date_start
            ver_end = version.contract_date_end
            eff_from = max(d_from, ver_start) if ver_start else d_from
            eff_to = min(d_to, ver_end) if ver_end else d_to
            if eff_from > eff_to:
                continue

            attendances = self.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', datetime.combine(eff_from, time.min)),
                ('check_in', '<=', datetime.combine(eff_to, time.max)),
            ])

            is_sheet = employee.sudo().x_is_attendance_sheet

            if is_sheet:
                res += self._worked_day_lines_sheet(
                    version, employee, attendances, eff_from, eff_to)
            elif attendances:
                res += self._worked_day_lines_biometric(
                    version, employee, attendances)
            else:
                # No KSW attendance data → standard om_hr_payroll logic
                res += super().get_worked_day_lines(
                    version, date_from, date_to)

        return res

    # ------------------------------------------------------------------
    # Attendance-sheet employees (attended / absent only)
    # ------------------------------------------------------------------

    def _worked_day_lines_sheet(self, version, employee, attendances,
                                date_from, date_to):
        """For attendance-sheet employees only attended vs absent matters.
        No late / early-leave tracking."""
        lines = []

        attended_count = len(attendances)
        attended_hours = round(sum(a.worked_hours or 0.0 for a in attendances))

        lines.append({
            'name': _('Attended Days'),
            'sequence': 1,
            'code': 'WORK100',
            'number_of_days': attended_count,
            'number_of_hours': attended_hours,
            'version_id': version.id,
        })

        # --- Absent days ---
        # Prefer the attendance-sheet lines for accuracy; fall back to a
        # simple calendar-days-minus-attended calculation.
        sheet = self.env['ksw.attendance.sheet'].sudo().search([
            ('employee_id', '=', employee.id),
            ('month', '=', str(date_from.month)),
            ('year', '=', date_from.year),
        ], limit=1)

        if sheet:
            absent_lines = sheet.line_ids.filtered(
                lambda l: date_from <= l.date <= date_to
                and not l.is_attended
            )
            absent_count = len(absent_lines)
        else:
            calendar_days = (date_to - date_from).days + 1
            absent_count = max(0, calendar_days - attended_count)

        if absent_count > 0:
            absent_hours = round(absent_count * DAILY_HOURS)

            # Compute monetary deduction for absent days
            v = employee.sudo().current_version_id or version
            base = (
                (v.wage or 0.0)
                + (v.da or 0.0)
                + (v.travel_allowance or 0.0)
                + (v.meal_allowance or 0.0)
                + (v.medical_allowance or 0.0)
                + (v.other_allowance or 0.0)
            )
            daily_rate = base / DAYS_PER_MONTH if base else 0.0
            deduction_total = round(daily_rate * absent_count)

            lines.append({
                'name': _('Absent Days'),
                'sequence': 2,
                'code': 'ATT_ABS',
                'number_of_days': absent_count,
                'number_of_hours': absent_hours,
                'amount': deduction_total,
                'version_id': version.id,
            })

            if deduction_total > 0:
                lines.append({
                    'name': _('Attendance Deduction'),
                    'sequence': 15,
                    'code': 'ATT_DED',
                    'number_of_days': absent_count,
                    'number_of_hours': 0,
                    'amount': deduction_total,
                    'version_id': version.id,
                })

        return lines

    # ------------------------------------------------------------------
    # Biometric employees (full issue tracking)
    # ------------------------------------------------------------------

    def _worked_day_lines_biometric(self, version, employee, attendances):
        """For biometric employees: worked, absent, late, early-leave,
        and the aggregated monetary deduction."""
        lines = []

        non_absent = attendances.filtered(lambda a: not a.x_net_is_absent)
        absent = attendances.filtered('x_net_is_absent')
        late = attendances.filtered(lambda a: a.x_net_late_minutes > 0)
        early = attendances.filtered(
            lambda a: a.x_net_early_leave_minutes > 0)

        # WORK100 — Actually worked days
        lines.append({
            'name': _('Worked Days'),
            'sequence': 1,
            'code': 'WORK100',
            'number_of_days': len(non_absent),
            'number_of_hours': round(sum(
                a.x_net_worked_hours or 0.0 for a in non_absent)),
            'version_id': version.id,
        })

        # ATT_ABS — Absent days
        if absent:
            abs_deduction = round(sum(
                a.x_deduction_amount or 0.0 for a in absent))
            lines.append({
                'name': _('Absent Days'),
                'sequence': 2,
                'code': 'ATT_ABS',
                'number_of_days': len(absent),
                'number_of_hours': round(len(absent) * DAILY_HOURS),
                'amount': abs_deduction,
                'version_id': version.id,
            })

        # Split non-absent deductions proportionally between late & early
        late_deduction_total = 0.0
        early_deduction_total = 0.0
        for a in non_absent:
            ded = a.x_deduction_amount or 0.0
            if ded <= 0:
                continue
            l_min = a.x_net_late_minutes or 0.0
            e_min = a.x_net_early_leave_minutes or 0.0
            total_min = l_min + e_min
            if total_min > 0:
                late_deduction_total += ded * l_min / total_min
                early_deduction_total += ded * e_min / total_min

        # ATT_LATE — Late arrivals
        if late:
            total_late_min = sum(a.x_net_late_minutes for a in late)
            lines.append({
                'name': _('Late Arrivals'),
                'sequence': 3,
                'code': 'ATT_LATE',
                'number_of_days': len(late),
                'number_of_hours': round(total_late_min / 60.0),
                'amount': round(late_deduction_total),
                'version_id': version.id,
            })

        # ATT_EARLY — Early departures
        if early:
            total_early_min = sum(
                a.x_net_early_leave_minutes for a in early)
            lines.append({
                'name': _('Early Departures'),
                'sequence': 4,
                'code': 'ATT_EARLY',
                'number_of_days': len(early),
                'number_of_hours': round(total_early_min / 60.0),
                'amount': round(early_deduction_total),
                'version_id': version.id,
            })

        # ATT_DED — Aggregated monetary deduction
        deduction_total = round(sum(
            a.x_deduction_amount or 0.0 for a in attendances))
        if deduction_total > 0:
            deduction_days = len(
                attendances.filtered(
                    lambda a: (a.x_deduction_amount or 0.0) > 0))
            lines.append({
                'name': _('Attendance Deduction'),
                'sequence': 15,
                'code': 'ATT_DED',
                'number_of_days': deduction_days,
                'number_of_hours': 0,
                'amount': deduction_total,
                'version_id': version.id,
            })

        return lines







