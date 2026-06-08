from datetime import datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

DAILY_HOURS = 8.0
DAYS_PER_MONTH = 30.0


# ======================================================================
# Extend worked-day line — display fields + deduction amount
# ======================================================================

# Maps worked-day code → (count_unit, value_unit)
_WD_UNITS = {
    'WORK100':   ('days',  'hours'),
    'ATT_ABS':   ('days',  'hours'),
    'ATT_LATE':  ('times', 'hours'),
    'ATT_EARLY': ('times', 'hours'),
    'ATT_DED':   ('',      ''),
}


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    number_of_days = fields.Float(digits=(16, 2))
    number_of_hours = fields.Float(digits=(16, 2))
    amount = fields.Float(
        string='Amount',
        digits=(16, 0),
        help='Monetary amount associated with this worked-day entry '
             '(e.g. total attendance deduction).',
    )

    x_count_display = fields.Char(
        string='Count', compute='_compute_display_fields',
    )
    x_value_display = fields.Char(
        string='Value', compute='_compute_display_fields',
    )

    @api.depends('code', 'number_of_days', 'number_of_hours')
    def _compute_display_fields(self):
        for rec in self:
            c_unit, v_unit = _WD_UNITS.get(rec.code or '', ('', ''))
            # Count
            days = rec.number_of_days or 0.0
            if not c_unit:
                rec.x_count_display = ''
            else:
                rec.x_count_display = '%.2f (%s)' % (days, c_unit)
            # Value
            hrs = rec.number_of_hours or 0.0
            if not v_unit:
                rec.x_value_display = ''
            else:
                rec.x_value_display = '%.2f (%s)' % (hrs, v_unit)


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
    # Reverse link to the leave that generated this vacation payslip
    # ------------------------------------------------------------------

    x_leave_id = fields.Many2one(
        'hr.leave', string='Related Leave', readonly=True, copy=False,
        help='The annual leave that triggered the creation of this '
             'vacation payslip.  Set automatically by '
             '_create_vacation_payslip().',
    )

    # ------------------------------------------------------------------
    # Daily / Hourly wage (read-only info fields)
    # ------------------------------------------------------------------

    x_daily_wage = fields.Float(
        string='Daily Wage',
        compute='_compute_wage_rates',
        digits=(16, 2),
        help='(Wage + DA + Travel + Meal + Medical + Other) / 30. '
             'Excludes housing allowance (HRA).',
    )
    x_hourly_wage = fields.Float(
        string='Hourly Wage',
        compute='_compute_wage_rates',
        digits=(16, 2),
        help='Daily wage / 8 hours.',
    )

    # ------------------------------------------------------------------
    # Net wage — stored so it can be shown in the batch payslip list
    # ------------------------------------------------------------------

    x_net_wage = fields.Float(
        string='Net Salary',
        compute='_compute_net_wage',
        store=True,
        digits=(16, 0),
        help='Total of the NET salary rule line after compute_sheet().',
    )

    @api.depends('line_ids.total', 'line_ids.code')
    def _compute_net_wage(self):
        for slip in self:
            net_lines = slip.line_ids.filtered(lambda l: l.code == 'NET')
            slip.x_net_wage = sum(net_lines.mapped('total'))

    @api.depends('version_id.wage',
                 'version_id.travel_allowance', 'version_id.mobile_allowance',
                 'version_id.other_allowance')
    def _compute_wage_rates(self):
        for slip in self:
            v = slip.version_id
            base = (
                (v.wage or 0.0)
                + (v.travel_allowance or 0.0)
                + (v.mobile_allowance or 0.0)
                + (v.other_allowance or 0.0)
            )
            daily = base / DAYS_PER_MONTH if base else 0.0
            slip.x_daily_wage = daily
            slip.x_hourly_wage = daily / DAILY_HOURS if daily else 0.0

    # ------------------------------------------------------------------
    # compute_sheet override
    # ------------------------------------------------------------------

    def compute_sheet(self):
        """Guard against unresolved vacations, ensure worked-day lines
        are populated, and inject prior-payslip adjustment inputs so
        fixed monthly amounts (HRA) are not paid twice.

        When a prior vacation payslip exists in the same period and the
        employee's return has been HR-confirmed, we re-generate worked-day
        lines starting from the return date so that pre-vacation attendance
        is NOT double-counted.
        """
        for payslip in self:
            self._check_unresolved_vacation(payslip)

            # Refresh VACATION_BAL on vacation payslips so that contract
            # date / wage changes are reflected when recomputing.
            self._refresh_vacation_bal_input(payslip)

            # If a vacation return exists, force re-generation of worked
            # days from the return date (not the payslip start).
            return_date = self._get_vacation_return_date(payslip)
            if return_date and payslip.worked_days_line_ids:
                payslip.worked_days_line_ids.unlink()

            if not payslip.worked_days_line_ids:
                self._ensure_worked_days(payslip, effective_from=return_date)

            self._inject_prior_hra_input(payslip)
        return super().compute_sheet()

    # ------------------------------------------------------------------
    # Refresh VACATION_BAL input on vacation payslips
    # ------------------------------------------------------------------

    def _refresh_vacation_bal_input(self, payslip):
        """Recompute the VACATION_BAL input line on a vacation payslip.

        This ensures that contract-date or wage changes on hr.version
        are reflected when the payslip is recomputed.  Only applies to
        vacation payslips (those linked to an annual leave via x_leave_id).
        """
        leave = payslip.x_leave_id
        if not leave:
            return

        employee = payslip.employee_id
        if not employee:
            return

        # Delegate to hr.leave._build_vacation_input_lines which knows
        # how to determine vacation_days from the leave type/flags.
        HrLeave = self.env['hr.leave'].sudo()
        new_vals = HrLeave._build_vacation_input_lines(leave, employee, payslip)

        # Extract the new VACATION_BAL entry
        new_vac = next((v for v in new_vals if v.get('code') == 'VACATION_BAL'), None)

        # Find the existing VACATION_BAL input line
        existing_vac = payslip.input_line_ids.filtered(lambda i: i.code == 'VACATION_BAL')

        if new_vac and existing_vac:
            existing_vac.sudo().write({
                'name': new_vac['name'],
                'amount': new_vac['amount'],
            })
        elif new_vac and not existing_vac:
            self.env['hr.payslip.input'].sudo().create(new_vac)
        elif not new_vac and existing_vac:
            existing_vac.sudo().unlink()

    # ------------------------------------------------------------------
    # Prevent double-payment of HRA across multiple payslips in a month
    # ------------------------------------------------------------------

    def _get_vacation_return_date(self, payslip):
        """Find the latest HR-confirmed annual-leave return date for the
        payslip's employee within the payslip period.

        Returns the return date (``date``) or ``None``.
        Leaves whose vacation payslip IS the current payslip are excluded
        (so the vacation payslip itself is never affected).
        """
        if not payslip.employee_id or not payslip.date_from or not payslip.date_to:
            return None

        confirmed_leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', payslip.employee_id.id),
            ('state', '=', 'validate'),
            ('holiday_status_id.is_annual_leave', '=', True),
            ('x_return_state', '=', 'hr_confirmed'),
            ('x_return_date', '!=', False),
            ('request_date_from', '<=', payslip.date_to),
            ('request_date_to', '>=', payslip.date_from),
        ])

        # Exclude leaves where this payslip is one of the vacation payslips
        if payslip.id:
            confirmed_leaves = confirmed_leaves.filtered(
                lambda l: payslip.id not in l.x_vacation_payslip_ids.ids
            )

        if not confirmed_leaves:
            return None

        # Return the latest return date
        return max(l.x_return_date for l in confirmed_leaves)

    def _inject_prior_hra_input(self, payslip):
        """If another confirmed/done payslip exists for the same employee
        in the same month, inject PRIOR_HRA and PRIOR_GOSI input lines so
        the HRA/GOSI rules can subtract the already-paid amounts.  This
        prevents HRA and GOSI from being paid twice when a vacation payslip
        and a regular monthly payslip coexist.

        Also considers vacation payslips in 'draft' state that are linked
        to validated annual leaves (auto-generated, not yet confirmed).
        For cross-month vacations, only payslips whose date range actually
        overlaps this payslip's period are included.
        """
        if not payslip.employee_id or not payslip.date_from or not payslip.date_to:
            return

        # Remove any existing PRIOR_HRA / PRIOR_GOSI inputs (in case of recompute)
        existing_prior = payslip.input_line_ids.filtered(
            lambda i: i.code in ('PRIOR_HRA', 'PRIOR_GOSI')
        )
        if existing_prior:
            existing_prior.unlink()

        # Find other non-cancelled payslips for the same employee whose
        # period overlaps the same month.
        domain = [
            ('employee_id', '=', payslip.employee_id.id),
            ('state', 'in', ('verify', 'done')),
            ('date_from', '<=', payslip.date_to),
            ('date_to', '>=', payslip.date_from),
        ]
        if payslip.id:
            domain.append(('id', '!=', payslip.id))

        prior_slips = self.env['hr.payslip'].sudo().search(domain)

        # Also include vacation payslips in 'draft' state that are linked
        # to validated annual leaves (auto-generated, not yet confirmed).
        # For cross-month vacations, only include payslips whose date range
        # actually overlaps this payslip's period.
        vacation_leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', payslip.employee_id.id),
            ('state', '=', 'validate'),
            ('holiday_status_id.is_annual_leave', '=', True),
            ('request_date_from', '<=', payslip.date_to),
            ('request_date_to', '>=', payslip.date_from),
        ])
        for leave in vacation_leaves:
            for vac_slip in leave.x_vacation_payslip_ids:
                if (vac_slip.state != 'cancel'
                        and vac_slip.id != payslip.id
                        and vac_slip not in prior_slips
                        and vac_slip.date_from <= payslip.date_to
                        and vac_slip.date_to >= payslip.date_from):
                    prior_slips |= vac_slip

        if not prior_slips:
            return

        # Sum HRA and GOSI already paid in prior payslips
        prior_hra = 0.0
        prior_gosi = 0.0
        for slip in prior_slips:
            for line in slip.line_ids:
                if line.code == 'HRA' and line.total > 0:
                    prior_hra += line.total
                elif line.code == 'GOSI' and line.total < 0:
                    prior_gosi += line.total  # negative value

        version_id = (
            payslip.version_id.id
            or (payslip.employee_id.current_version_id
                and payslip.employee_id.current_version_id.id)
        )
        if not version_id:
            return

        slip_refs = ', '.join(prior_slips.mapped('number') or prior_slips.mapped('name'))

        if prior_hra > 0:
            self.env['hr.payslip.input'].sudo().create({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': 'HRA already paid in %s' % slip_refs,
                'code': 'PRIOR_HRA',
                'amount': prior_hra,
                'sequence': 5,
            })

        if prior_gosi < 0:
            # Store as positive so the GOSI rule can add it back:
            # result = min(gosi + prior_gosi_input, 0)
            self.env['hr.payslip.input'].sudo().create({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': 'GOSI already paid in %s' % slip_refs,
                'code': 'PRIOR_GOSI',
                'amount': abs(prior_gosi),
                'sequence': 6,
            })

    # ------------------------------------------------------------------
    # Vacation-return guard
    # ------------------------------------------------------------------

    @api.model
    def _get_unresolved_vacation_leaves(self, employee_id, date_to,
                                        exclude_payslip_id=None):
        """Return validated annual-leave records whose return is still
        pending (x_return_state == 'on_vacation').

        :param employee_id: int — employee DB id
        :param date_to: date — payslip end date
        :param exclude_payslip_id: int|None — exclude leaves whose
               vacation payslip IS this payslip (avoids self-blocking)
        :return: hr.leave recordset (may be empty)
        """
        if not employee_id or not date_to:
            return self.env['hr.leave']
        unresolved = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'validate'),
            ('holiday_status_id.is_annual_leave', '=', True),
            ('x_return_state', '=', 'on_vacation'),
            ('request_date_from', '<=', date_to),
        ])
        if exclude_payslip_id:
            unresolved = unresolved.filtered(
                lambda l: exclude_payslip_id not in l.x_vacation_payslip_ids.ids
            )
        return unresolved

    def _check_unresolved_vacation(self, payslip):
        """Raise ValidationError if the employee has an unresolved
        vacation return for the payslip period.

        Leaves whose vacation payslip IS the current payslip are excluded
        (so recomputing the vacation payslip itself doesn't block).
        """
        if not payslip.employee_id or not payslip.date_to:
            return
        unresolved = self._get_unresolved_vacation_leaves(
            payslip.employee_id.id,
            payslip.date_to,
            exclude_payslip_id=payslip.id,
        )
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

    def _ensure_worked_days(self, payslip, effective_from=None):
        """Populate worked_days_line_ids when they are empty (e.g. batch
        payslip generation where the UI onchange never fires).

        When *effective_from* is given (e.g. a vacation return date), it
        replaces ``payslip.date_from`` so that only attendance **from that
        date onwards** is counted — pre-vacation days are not
        double-counted.

        Because salary rules always compute full-month amounts (e.g.
        BASIC = wage), the pre-return calendar days must still appear as
        absent so that ATTDED deducts the correct amount.  Otherwise the
        employee would receive almost an entire extra month's salary on
        the monthly payslip.
        """
        version_ids = (
            payslip.version_id.ids
            or self.get_versions(
                payslip.employee_id, payslip.date_from, payslip.date_to)
        )
        if not version_ids:
            return
        versions = self.env['hr.version'].browse(version_ids)
        start = effective_from or payslip.date_from
        wd_vals = self.get_worked_day_lines(
            versions, start, payslip.date_to)

        # When effective_from shifts the attendance window, add the
        # pre-return calendar days as absent so ATTDED fires correctly.
        if effective_from and wd_vals:
            pre_return_days = (effective_from - payslip.date_from).days
            if pre_return_days > 0:
                self._add_pre_return_absent_days(
                    wd_vals, pre_return_days, versions[:1])

        if wd_vals:
            payslip.worked_days_line_ids = [
                (0, 0, v) for v in wd_vals
            ]

    def _add_pre_return_absent_days(self, wd_vals, pre_return_days, version):
        """Inject pre-return calendar days into ATT_ABS / ATT_DED lines.

        When the monthly payslip only counts attendance from the vacation
        return date, the days between ``payslip.date_from`` and the return
        date are *not* covered by any attendance.  Salary rules always
        fire at full-month amounts, so these days must appear as absent
        with a corresponding deduction so the employee doesn't receive a
        double salary.
        """
        v = version.employee_id.sudo().current_version_id or version
        base = (
            (v.wage or 0.0)
            + (v.travel_allowance or 0.0)
            + (v.mobile_allowance or 0.0)
            + (v.other_allowance or 0.0)
        )
        daily_rate = base / DAYS_PER_MONTH if base else 0.0
        pre_return_deduction = round(daily_rate * pre_return_days)
        pre_return_hours = round(pre_return_days * DAILY_HOURS, 2)

        # Update or create ATT_ABS
        att_abs = next((d for d in wd_vals if d.get('code') == 'ATT_ABS'),
                       None)
        if att_abs:
            att_abs['number_of_days'] += pre_return_days
            att_abs['number_of_hours'] = round(
                att_abs.get('number_of_hours', 0) + pre_return_hours, 2)
            att_abs['amount'] = (att_abs.get('amount', 0)
                                 + pre_return_deduction)
        else:
            wd_vals.append({
                'name': _('Absent Days'),
                'sequence': 2,
                'code': 'ATT_ABS',
                'number_of_days': pre_return_days,
                'number_of_hours': pre_return_hours,
                'amount': pre_return_deduction,
                'version_id': version.id,
            })

        # Update or create ATT_DED
        if pre_return_deduction > 0:
            att_ded = next(
                (d for d in wd_vals if d.get('code') == 'ATT_DED'), None)
            if att_ded:
                att_ded['number_of_days'] += pre_return_days
                att_ded['amount'] = (att_ded.get('amount', 0)
                                     + pre_return_deduction)
            else:
                wd_vals.append({
                    'name': _('Attendance Deduction'),
                    'sequence': 15,
                    'code': 'ATT_DED',
                    'number_of_days': pre_return_days,
                    'number_of_hours': 0,
                    'amount': pre_return_deduction,
                    'version_id': version.id,
                })

        # Legacy compatibility: some payroll structures still reference
        # ``MISDAYS`` for the same deduction concept.
        if pre_return_deduction > 0:
            misdays = next((d for d in wd_vals if d.get('code') == 'MISDAYS'), None)
            if misdays:
                misdays['number_of_days'] += pre_return_days
                misdays['amount'] = (misdays.get('amount', 0)
                                     + pre_return_deduction)
            else:
                wd_vals.append({
                    'name': _('Missing Days'),
                    'sequence': 16,
                    'code': 'MISDAYS',
                    'number_of_days': pre_return_days,
                    'number_of_hours': pre_return_hours,
                    'amount': pre_return_deduction,
                    'version_id': version.id,
                })

    # ------------------------------------------------------------------
    # get_worked_day_lines — main override
    # ------------------------------------------------------------------

    @api.model
    def get_worked_day_lines(self, versions, date_from, date_to):
        """Build worked-day lines from actual hr.attendance records.

        * Attendance-sheet employees  → attended / absent days only.
        * All other employees (biometric) → attended, absent, late, early,
          plus monetary deduction total.  When no attendance records exist
          for the period, all calendar days are counted as unpresented.
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
            else:
                # Biometric employees — always use attendance-based logic.
                # When attendances is empty (e.g. future days, or employee
                # didn't check in), all calendar days are counted as
                # unpresented / absent.  We do NOT fall back to the
                # standard om_hr_payroll calendar logic because it relies
                # on attendance_ids which are empty in this project
                # (calendar_group_ids is used instead).
                res += self._worked_day_lines_biometric(
                    version, employee, attendances, eff_from, eff_to)

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
        attended_hours = sum(a.worked_hours or 0.0 for a in attendances)

        lines.append({
            'name': _('Attended Days'),
            'sequence': 1,
            'code': 'WORK100',
            'number_of_days': attended_count,
            'number_of_hours': round(attended_hours, 2),
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
            absent_hours = round(absent_count * DAILY_HOURS, 2)

            # Compute monetary deduction for absent days
            v = employee.sudo().current_version_id or version
            base = (
                (v.wage or 0.0)
                + (v.travel_allowance or 0.0)
                + (v.mobile_allowance or 0.0)
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

                # Legacy compatibility alias for older payroll structures.
                lines.append({
                    'name': _('Missing Days'),
                    'sequence': 16,
                    'code': 'MISDAYS',
                    'number_of_days': absent_count,
                    'number_of_hours': 0,
                    'amount': deduction_total,
                    'version_id': version.id,
                })

        return lines

    # ------------------------------------------------------------------
    # Biometric employees (full issue tracking)
    # ------------------------------------------------------------------

    def _worked_day_lines_biometric(self, version, employee, attendances,
                                    date_from, date_to):
        """For biometric employees: worked, absent, late, early-leave,
        unpresented days (no attendance record), and the aggregated
        monetary deduction."""
        lines = []

        non_absent = attendances.filtered(lambda a: not a.x_net_is_absent)
        absent = attendances.filtered('x_net_is_absent')
        late = attendances.filtered(lambda a: a.x_net_late_minutes > 0)
        early = attendances.filtered(
            lambda a: a.x_net_early_leave_minutes > 0)

        # --- Unpresented days (calendar days with no attendance record) ---
        attended_dates = {a.check_in.date() for a in attendances if a.check_in}
        total_calendar_days = (date_to - date_from).days + 1
        unpresented_count = max(0, total_calendar_days - len(attended_dates))

        # Daily rate for unpresented-day deduction (same formula as sheet)
        v = employee.sudo().current_version_id or version
        base = (
            (v.wage or 0.0)
            + (v.travel_allowance or 0.0)
            + (v.mobile_allowance or 0.0)
            + (v.other_allowance or 0.0)
        )
        daily_rate = base / DAYS_PER_MONTH if base else 0.0
        unpresented_deduction = round(daily_rate * unpresented_count)

        # WORK100 — Actually worked days
        lines.append({
            'name': _('Worked Days'),
            'sequence': 1,
            'code': 'WORK100',
            'number_of_days': len(non_absent),
            'number_of_hours': round(sum(
                a.x_net_worked_hours or 0.0 for a in non_absent), 2),
            'version_id': version.id,
        })

        # ATT_ABS — Absent days (record-based + unpresented)
        record_absent_count = len(absent)
        record_absent_deduction = round(sum(
            a.x_deduction_amount or 0.0 for a in absent))
        total_absent_count = record_absent_count + unpresented_count
        total_absent_deduction = record_absent_deduction + unpresented_deduction

        if total_absent_count > 0:
            lines.append({
                'name': _('Absent Days'),
                'sequence': 2,
                'code': 'ATT_ABS',
                'number_of_days': total_absent_count,
                'number_of_hours': round(total_absent_count * DAILY_HOURS, 2),
                'amount': total_absent_deduction,
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
                'number_of_hours': round(total_late_min / 60.0, 2),
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
                'number_of_hours': round(total_early_min / 60.0, 2),
                'amount': round(early_deduction_total),
                'version_id': version.id,
            })

        # ATT_DED — Aggregated monetary deduction (records + unpresented)
        record_deduction = round(sum(
            a.x_deduction_amount or 0.0 for a in attendances))
        deduction_total = record_deduction + unpresented_deduction
        if deduction_total > 0:
            record_ded_days = len(
                attendances.filtered(
                    lambda a: (a.x_deduction_amount or 0.0) > 0))
            deduction_days = record_ded_days + unpresented_count
            lines.append({
                'name': _('Attendance Deduction'),
                'sequence': 15,
                'code': 'ATT_DED',
                'number_of_days': deduction_days,
                'number_of_hours': 0,
                'amount': deduction_total,
                'version_id': version.id,
            })

            # Legacy compatibility alias for older payroll structures.
            lines.append({
                'name': _('Missing Days'),
                'sequence': 16,
                'code': 'MISDAYS',
                'number_of_days': deduction_days,
                'number_of_hours': 0,
                'amount': deduction_total,
                'version_id': version.id,
            })

        return lines

    def get_deduction_breakdown(self):
        """Return a list of dicts for the payslip report's Attendance
        Deduction Breakdown section.  Includes both attendance records
        with deductions AND unpresented calendar days (no attendance
        record at all), so the breakdown total matches ATT_DED.
        """
        self.ensure_one()
        rows = []

        d_from = self.date_from
        d_to = self.date_to
        employee = self.employee_id
        if not employee or not d_from or not d_to:
            return rows

        # Daily rate for absent / unpresented days
        v = employee.sudo().current_version_id
        base = (
            (v.wage or 0.0)
            + (v.travel_allowance or 0.0)
            + (v.mobile_allowance or 0.0)
            + (v.other_allowance or 0.0)
        ) if v else 0.0
        daily_rate = base / DAYS_PER_MONTH if base else 0.0

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                     'Friday', 'Saturday', 'Sunday']

        # Check for vacation return — must mirror the worked-day logic
        return_date = self._get_vacation_return_date(self)
        eff_from = return_date if return_date else d_from

        # Pre-return days (vacation period) — all counted as absent
        if return_date and return_date > d_from:
            current = d_from
            while current < return_date:
                rows.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'day': day_names[current.weekday()],
                    'late_min': 0,
                    'early_min': 0,
                    'is_absent': True,
                    'deduction': daily_rate,
                    'type': 'pre_return',
                })
                current += timedelta(days=1)

        # Attendance records with deductions (from effective start)
        att_recs = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', datetime.combine(eff_from, time.min)),
            ('check_in', '<=', datetime.combine(d_to, time.max)),
            ('x_deduction_amount', '>', 0),
        ], order='check_in asc')

        for att in att_recs:
            # For absent records, use the exact daily_rate (not the
            # rounded x_deduction_amount) so all absent rows are
            # consistent with unpresented-day rows.
            if att.x_net_is_absent:
                ded = daily_rate
            else:
                ded = att.x_deduction_amount or 0
            rows.append({
                'date': att.check_in.strftime('%Y-%m-%d'),
                'day': att.x_day_of_week or '',
                'late_min': att.x_net_late_minutes or 0,
                'early_min': att.x_net_early_leave_minutes or 0,
                'is_absent': att.x_net_is_absent,
                'deduction': ded,
                'type': 'absent' if att.x_net_is_absent else 'issue',
            })

        # Unpresented days (from effective start, no attendance at all)
        all_att = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', datetime.combine(eff_from, time.min)),
            ('check_in', '<=', datetime.combine(d_to, time.max)),
        ])
        attended_dates = {a.check_in.date() for a in all_att if a.check_in}

        current = eff_from
        while current <= d_to:
            if current not in attended_dates:
                rows.append({
                    'date': current.strftime('%Y-%m-%d'),
                    'day': day_names[current.weekday()],
                    'late_min': 0,
                    'early_min': 0,
                    'is_absent': True,
                    'deduction': daily_rate,
                    'type': 'unpresented',
                })
            current += timedelta(days=1)

        # Sort by date
        rows.sort(key=lambda r: r['date'])
        return rows
