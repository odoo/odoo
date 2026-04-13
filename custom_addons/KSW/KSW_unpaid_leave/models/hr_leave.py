from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrLeaveUnpaid(models.Model):
    _inherit = 'hr.leave'

    # ------------------------------------------------------------------
    # Unpaid-specific accounting fields (filled by Accountant)
    # ------------------------------------------------------------------

    x_financial_consideration_excess = fields.Float(
        string='Financial Consideration for Excess Leave',
        digits=(16, 2), copy=False, tracking=True,
        help='Financial consideration for excess unpaid leave days (filled by Accounting).',
    )
    x_financial_consideration_excess_description = fields.Text(
        string='Financial Consideration Description', copy=False,
    )
    x_visa_cost_recovery = fields.Float(
        string='Visa Cost Recovery for Excess Leave',
        digits=(16, 2), copy=False, tracking=True,
        help='Visa cost recovery for excess unpaid leave days (filled by Accounting).',
    )
    x_visa_cost_recovery_description = fields.Text(
        string='Visa Cost Recovery Description', copy=False,
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_unpaid_leave(self, leave):
        """Check if the leave type is flagged as unpaid leave."""
        return (
            leave.holiday_status_id
            and leave.holiday_status_id.is_unpaid_leave
        )

    def _is_unpaid_multi(self, leave):
        """Check if the leave type uses unpaid multi-step approval."""
        return (
            leave.holiday_status_id
            and leave.holiday_status_id.leave_validation_type == 'unpaid_multi'
        )

    # ------------------------------------------------------------------
    # Duration: calendar-day counting (same as annual, no full-clearance)
    # ------------------------------------------------------------------

    @api.depends('holiday_status_id')
    def _compute_duration(self):
        unpaid = self.filtered(self._is_unpaid_leave)
        remaining = self - unpaid
        if remaining:
            super(HrLeaveUnpaid, remaining)._compute_duration()
        for leave in unpaid:
            cal_days, cal_hours = self._annual_cal_days(leave)
            leave.number_of_days = cal_days
            leave.number_of_hours = cal_hours
            # Ensure full-clearance fields stay 0 for unpaid
            leave.x_actual_vacation_days = 0
            leave.x_clearance_balance = 0

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        unpaid = self.filtered(self._is_unpaid_leave)
        remaining = self - unpaid
        result = {}
        if remaining:
            result.update(super(HrLeaveUnpaid, remaining)._get_durations(
                check_leave_type=check_leave_type,
                resource_calendar=resource_calendar,
            ))
        for leave in unpaid:
            result[leave.id] = self._annual_cal_days(leave)
        return result

    def _get_number_of_days(self, date_from, date_to, employee_id):
        if self and self._is_unpaid_leave(self):
            if date_from and date_to:
                start = (
                    date_from.date() if hasattr(date_from, 'date')
                    else date_from
                )
                end = (
                    date_to.date() if hasattr(date_to, 'date')
                    else date_to
                )
                cal_days = (end - start).days + 1
                employee = self.env['hr.employee'].browse(employee_id)
                daily_hours = (
                    self._get_daily_work_hours(employee)
                    if employee_id else 8.0
                )
                return {'days': cal_days, 'hours': cal_days * daily_hours}
            return {'days': 0, 'hours': 0}
        return super()._get_number_of_days(date_from, date_to, employee_id)

    # ------------------------------------------------------------------
    # Hide standard approve/validate for unpaid_multi
    # ------------------------------------------------------------------

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        unpaid_multi = self.filtered(self._is_unpaid_multi)
        remaining = self - unpaid_multi
        if remaining:
            super(HrLeaveUnpaid, remaining)._compute_can_approve()
        for leave in unpaid_multi:
            leave.can_approve = False

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_validate(self):
        unpaid_multi = self.filtered(self._is_unpaid_multi)
        remaining = self - unpaid_multi
        if remaining:
            super(HrLeaveUnpaid, remaining)._compute_can_validate()
        for leave in unpaid_multi:
            leave.can_validate = False

    # ------------------------------------------------------------------
    # Create hook — start multi-step chain
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for leave in records:
            if self._is_unpaid_multi(leave):
                leave.sudo().write({
                    'x_annual_approval_state': 'pending_dm',
                })
        return records

    # ------------------------------------------------------------------
    # action_approve intercept
    # ------------------------------------------------------------------

    def action_approve(self, check_state=True):
        unpaid_multi = self.filtered(self._is_unpaid_multi)
        remaining = self - unpaid_multi
        if unpaid_multi:
            for leave in unpaid_multi:
                if leave.x_annual_approval_state == 'pending_dm':
                    leave.action_dm_approve()
        if remaining:
            return super(HrLeaveUnpaid, remaining).action_approve(
                check_state=check_state)
        return True

    # ------------------------------------------------------------------
    # Override Accounting Approve for unpaid — no payslip fields,
    # just record unpaid-specific accounting fields
    # ------------------------------------------------------------------

    def action_acc_approve(self):
        """Override: for unpaid leaves, log the unpaid accounting fields."""
        unpaid = self.filtered(self._is_unpaid_leave)
        remaining = self - unpaid

        if remaining:
            super(HrLeaveUnpaid, remaining).action_acc_approve()

        for leave in unpaid:
            self._check_group(
                'KSW_annual_leave.group_annual_leave_acc',
                'Only Accounting Approvers can approve this step.',
            )
            if leave.x_annual_approval_state != 'pending_acc':
                raise UserError(
                    'This leave is not pending accounting approval.')
            leave.write({
                'x_annual_approval_state': 'pending_gm_final',
                'x_acc_approved_by': self.env.user.employee_id.id,
                'x_acc_approved_date': fields.Datetime.now(),
            })
            body_parts = [
                '<strong>✅ Step 4 — Accounting Approval '
                '(Unpaid)</strong><br/>',
                '<b>Approved by:</b> %s<br/>' % self.env.user.name,
            ]
            if leave.x_financial_consideration_excess:
                body_parts.append(
                    '<b>Financial Consideration for Excess Leave:</b> '
                    '%.2f SAR' % leave.x_financial_consideration_excess)
                if leave.x_financial_consideration_excess_description:
                    body_parts.append(
                        ' — %s'
                        % leave.x_financial_consideration_excess_description)
                body_parts.append('<br/>')
            if leave.x_visa_cost_recovery:
                body_parts.append(
                    '<b>Visa Cost Recovery for Excess Leave:</b> '
                    '%.2f SAR' % leave.x_visa_cost_recovery)
                if leave.x_visa_cost_recovery_description:
                    body_parts.append(
                        ' — %s'
                        % leave.x_visa_cost_recovery_description)
                body_parts.append('<br/>')
            leave.message_post(
                body=Markup(''.join(body_parts)),
                subtype_xmlid='mail.mt_note',
            )

    # ------------------------------------------------------------------
    # Override GM Final → no payslip, no return tracking for unpaid
    # ------------------------------------------------------------------

    def action_gm_final_approve(self):
        """Override: for unpaid leaves, skip payslip and return tracking."""
        unpaid = self.filtered(self._is_unpaid_leave)
        remaining = self - unpaid

        if remaining:
            super(HrLeaveUnpaid, remaining).action_gm_final_approve()

        if unpaid:
            for leave in unpaid:
                self._check_group(
                    'KSW_annual_leave.group_annual_leave_gm',
                    'Only the General Manager can give final approval.',
                )
                if leave.x_annual_approval_state != 'pending_gm_final':
                    raise UserError(
                        'This leave is not pending GM final approval.')

                leave.write({
                    'x_annual_approval_state': 'approved',
                    'x_gm_final_approved_by':
                        self.env.user.employee_id.id,
                    'x_gm_final_approved_date': fields.Datetime.now(),
                })
                # NO payslip creation for unpaid leave
                leave.message_post(
                    body=Markup(
                        '<strong>✅ Step 5 — GM Final Approval '
                        '(Unpaid)</strong>'
                        '<br/><b>Approved by:</b> %(approver)s<br/>'
                        '<b>Status:</b> Fully approved — no payslip.'
                    ) % {'approver': self.env.user.name},
                    subtype_xmlid='mail.mt_note',
                )

            # Standard Odoo validation
            unpaid._action_validate(check_state=False)

    # ------------------------------------------------------------------
    # _action_validate — lock attendance sheet lines + refresh accrual
    # ------------------------------------------------------------------

    def _reset_annual_multi_fields(self):
        """Extend reset to also clear unpaid-specific accounting fields."""
        super()._reset_annual_multi_fields()
        self.write({
            'x_financial_consideration_excess': 0,
            'x_financial_consideration_excess_description': False,
            'x_visa_cost_recovery': 0,
            'x_visa_cost_recovery_description': False,
        })

    def _action_validate(self, check_state=True):
        result = super()._action_validate(check_state=check_state)

        unpaid = self.filtered(self._is_unpaid_leave)
        if unpaid:
            # Do NOT set x_return_state for unpaid leaves — no return
            # tracking needed.  (The parent sets 'on_vacation' only for
            # annual leaves, so we don't need to undo anything here.)

            for leave in unpaid:
                self._lock_attendance_sheet_lines(leave)

            # Refresh accrual — unpaid days now reduce effective service
            emp_ids = unpaid.mapped('employee_id').ids
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(
                emp_ids)

        return result

    # ------------------------------------------------------------------
    # action_refuse / reset / draft / unlink — unlock lines + accrual
    # ------------------------------------------------------------------

    def action_refuse(self):
        unpaid = self.filtered(self._is_unpaid_leave)
        unpaid_multi = self.filtered(self._is_unpaid_multi)
        unpaid_emp_ids = unpaid.mapped('employee_id').ids

        # Unlock BEFORE super (super may change state)
        for leave in unpaid:
            self._unlock_attendance_sheet_lines(leave)

        result = super().action_refuse()

        if unpaid_multi:
            unpaid_multi._reset_annual_multi_fields()

        if unpaid_emp_ids:
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(
                unpaid_emp_ids)

        return result

    def _move_validate_leave_to_confirm(self):
        unpaid_multi = self.filtered(self._is_unpaid_multi)
        unpaid = self.filtered(self._is_unpaid_leave)
        unpaid_emp_ids = unpaid.mapped('employee_id').ids

        for leave in unpaid:
            self._unlock_attendance_sheet_lines(leave)

        if unpaid_multi:
            unpaid_multi._reset_annual_multi_fields()

        result = super()._move_validate_leave_to_confirm()

        if unpaid_multi:
            unpaid_multi.write({'x_annual_approval_state': 'pending_dm'})

        if unpaid_emp_ids:
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(
                unpaid_emp_ids)

        return result

    def action_draft(self):
        unpaid_emp_ids = self.filtered(
            self._is_unpaid_leave).mapped('employee_id').ids

        for leave in self.filtered(self._is_unpaid_leave):
            self._unlock_attendance_sheet_lines(leave)

        result = super().action_draft()

        unpaid_multi = self.filtered(self._is_unpaid_multi)
        if unpaid_multi:
            unpaid_multi._reset_annual_multi_fields()
            for leave in unpaid_multi:
                leave.x_annual_approval_state = 'pending_dm'

        if unpaid_emp_ids:
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(
                unpaid_emp_ids)

        return result

    def unlink(self):
        unpaid = self.filtered(self._is_unpaid_leave)
        unpaid_emp_ids = unpaid.mapped('employee_id').ids

        for leave in unpaid:
            self._unlock_attendance_sheet_lines(leave)

        result = super().unlink()

        if unpaid_emp_ids:
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(
                unpaid_emp_ids)

        return result

    # ------------------------------------------------------------------
    # Attendance sheet line lock / unlock
    # ------------------------------------------------------------------

    def _lock_attendance_sheet_lines(self, leave):
        """Mark attendance sheet lines as absent and lock them for the
        leave's date range.  Only affects sheet-type employees."""
        if not leave.employee_id or not leave.request_date_from:
            return
        # Only for attendance-sheet employees
        if not leave.employee_id.sudo().x_is_attendance_sheet:
            return

        date_from = leave.request_date_from
        date_to = leave.request_date_to or date_from

        lines = self.env['ksw.attendance.sheet.line'].sudo().search([
            ('sheet_id.employee_id', '=', leave.employee_id.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('x_leave_id', '=', False),
        ])
        if lines:
            # Bypass the leave-lock check in write() by writing
            # is_attended first, then x_leave_id
            for line in lines:
                # Use super's write to bypass our leave-lock guard
                super(type(line), line).write({
                    'is_attended': False,
                })
                line.sudo().write({'x_leave_id': leave.id})
            # Sync attendance records (delete auto-generated ones)
            for sheet in lines.mapped('sheet_id'):
                sheet._sync_line_attendance(
                    lines.filtered(lambda l: l.sheet_id == sheet))

    def _unlock_attendance_sheet_lines(self, leave):
        """Restore attendance sheet lines locked by this leave."""
        lines = self.env['ksw.attendance.sheet.line'].sudo().search([
            ('x_leave_id', '=', leave.id),
        ])
        if lines:
            # Clear the lock first, then restore attended
            lines.write({'x_leave_id': False})
            for line in lines:
                super(type(line), line).write({
                    'is_attended': True,
                })
            # Re-sync attendance records
            for sheet in lines.mapped('sheet_id'):
                sheet._sync_line_attendance(
                    lines.filtered(lambda l: l.sheet_id == sheet))






