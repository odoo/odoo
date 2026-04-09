from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError

ANNUAL_MULTI_STATES = [
    ('pending_dm', 'Pending DM Approval'),
    ('pending_hr', 'Pending HR Approval'),
    ('pending_gm_initial', 'Pending GM Initial'),
    ('pending_acc', 'Pending Accounting'),
    ('pending_gm_final', 'Pending GM Final'),
    ('approved', 'Approved'),
]


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    # ------------------------------------------------------------------
    # Annual-leave duration: calendar days (including weekends/holidays)
    # per Saudi labor law.  Only applies to leave types flagged with
    # is_annual_leave = True.
    # ------------------------------------------------------------------

    def _is_annual_leave(self, leave):
        """Check if the leave type is flagged as annual leave."""
        return (
            leave.holiday_status_id
            and leave.holiday_status_id.is_annual_leave
        )

    def _is_annual_multi(self, leave):
        """Check if the leave type uses multi-step approval."""
        return (
            leave.holiday_status_id
            and leave.holiday_status_id.leave_validation_type == 'annual_multi'
        )

    def _annual_cal_days(self, leave):
        """Return (days, hours) using calendar-day counting for annual leave."""
        if leave.request_date_from and leave.request_date_to:
            cal_days = (leave.request_date_to - leave.request_date_from).days + 1
            daily_hours = (
                self._get_daily_work_hours(leave.employee_id)
                if leave.employee_id else 8.0
            )
            return (cal_days, cal_days * daily_hours)
        return (0, 0)

    def _get_remaining_balance(self, leave):
        """Get the remaining annual leave balance for an employee."""
        if not leave.employee_id or not leave.holiday_status_id:
            return 0.0
        ksw_rec = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', leave.employee_id.id),
        ], limit=1)
        return ksw_rec.remaining_balance if ksw_rec else 0.0

    # ------------------------------------------------------------------
    # Full Balance Clearance
    # ------------------------------------------------------------------

    x_is_full_clearance = fields.Boolean(
        string='Full Balance Clearance',
        default=False, copy=False, tracking=True,
        help='When checked, this leave consumes the entire remaining '
             'annual leave balance instead of only the requested days.',
    )
    x_actual_vacation_days = fields.Float(
        string='Actual Vacation Days',
        digits=(10, 4), readonly=True, copy=False,
        help='The real number of calendar days the employee is on vacation '
             '(from request dates). Shown when Full Balance Clearance is used.',
    )
    x_clearance_balance = fields.Float(
        string='Balance Consumed',
        digits=(10, 4), readonly=True, copy=False,
        help='The full remaining balance consumed by this clearance leave.',
    )

    # ==================================================================
    # Multi-Step Approval Fields
    # ==================================================================

    x_annual_approval_state = fields.Selection(
        ANNUAL_MULTI_STATES,
        string='Approval Progress',
        copy=False, tracking=True, store=True,
        help='Tracks the multi-step annual leave approval chain.',
    )

    # --- HR-filled fields (penalty & iqama renewal) ---
    x_penalty_amount = fields.Float(
        string='Penalty Amount', digits=(16, 2), copy=False, tracking=True,
        help='Penalty amount to deduct from the vacation payslip (filled by HR).',
    )
    x_penalty_description = fields.Text(
        string='Penalty Description', copy=False,
    )
    x_iqama_renewal_amount = fields.Float(
        string='Iqama Renewal Amount', digits=(16, 2), copy=False, tracking=True,
        help='Iqama renewal cost to deduct from the vacation payslip (filled by HR).',
    )
    x_iqama_renewal_description = fields.Text(
        string='Iqama Renewal Description', copy=False,
    )

    # --- Accounting-filled fields (flight ticket) ---
    x_flight_ticket_amount = fields.Float(
        string='Flight Ticket Amount', digits=(16, 2), copy=False, tracking=True,
        help='Flight ticket allowance to add to the vacation payslip (filled by Accounting).',
    )
    x_flight_ticket_description = fields.Text(
        string='Flight Ticket Description', copy=False,
    )

    # --- Approver tracking ---
    x_dm_approved_by = fields.Many2one(
        'hr.employee', string='DM Approved By', readonly=True, copy=False,
    )
    x_dm_approved_date = fields.Datetime(
        string='DM Approved On', readonly=True, copy=False,
    )
    x_hr_approved_by = fields.Many2one(
        'hr.employee', string='HR Approved By', readonly=True, copy=False,
    )
    x_hr_approved_date = fields.Datetime(
        string='HR Approved On', readonly=True, copy=False,
    )
    x_gm_initial_approved_by = fields.Many2one(
        'hr.employee', string='GM Initial Approved By', readonly=True, copy=False,
    )
    x_gm_initial_approved_date = fields.Datetime(
        string='GM Initial Approved On', readonly=True, copy=False,
    )
    x_acc_approved_by = fields.Many2one(
        'hr.employee', string='ACC Approved By', readonly=True, copy=False,
    )
    x_acc_approved_date = fields.Datetime(
        string='ACC Approved On', readonly=True, copy=False,
    )
    x_gm_final_approved_by = fields.Many2one(
        'hr.employee', string='GM Final Approved By', readonly=True, copy=False,
    )
    x_gm_final_approved_date = fields.Datetime(
        string='GM Final Approved On', readonly=True, copy=False,
    )

    # --- Link to vacation payslip ---
    # x_vacation_payslip_id lives in KSW_payroll (depends on om_hr_payroll).

    # ==================================================================
    # Duration computation (annual-leave calendar-day counting)
    # ==================================================================

    @api.depends('holiday_status_id', 'x_is_full_clearance')
    def _compute_duration(self):
        annual = self.filtered(self._is_annual_leave)
        remaining = self - annual

        if remaining:
            super(HrLeave, remaining)._compute_duration()

        for leave in annual:
            cal_days, cal_hours = self._annual_cal_days(leave)
            if leave.x_is_full_clearance and cal_days > 0:
                balance = self._get_remaining_balance(leave)
                if balance > 0:
                    daily_hours = cal_hours / cal_days if cal_days else 8.0
                    leave.number_of_days = balance
                    leave.number_of_hours = balance * daily_hours
                    leave.x_actual_vacation_days = cal_days
                    leave.x_clearance_balance = balance
                else:
                    leave.number_of_days = cal_days
                    leave.number_of_hours = cal_hours
                    leave.x_actual_vacation_days = cal_days
                    leave.x_clearance_balance = 0
            else:
                leave.number_of_days = cal_days
                leave.number_of_hours = cal_hours
                leave.x_actual_vacation_days = 0
                leave.x_clearance_balance = 0

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        annual = self.filtered(self._is_annual_leave)
        remaining = self - annual

        result = {}
        if remaining:
            result.update(super(HrLeave, remaining)._get_durations(
                check_leave_type=check_leave_type,
                resource_calendar=resource_calendar,
            ))

        for leave in annual:
            if leave.x_is_full_clearance and leave.x_clearance_balance > 0:
                daily_hours = (
                    self._get_daily_work_hours(leave.employee_id)
                    if leave.employee_id else 8.0
                )
                result[leave.id] = (leave.x_clearance_balance,
                                    leave.x_clearance_balance * daily_hours)
            else:
                result[leave.id] = self._annual_cal_days(leave)

        return result

    def _get_number_of_days(self, date_from, date_to, employee_id):
        if self and self._is_annual_leave(self):
            if date_from and date_to:
                start = date_from.date() if hasattr(date_from, 'date') else date_from
                end = date_to.date() if hasattr(date_to, 'date') else date_to
                cal_days = (end - start).days + 1
                employee = self.env['hr.employee'].browse(employee_id)
                daily_hours = (
                    self._get_daily_work_hours(employee)
                    if employee_id else 8.0
                )
                if self.x_is_full_clearance:
                    balance = self._get_remaining_balance(self)
                    if balance > 0:
                        return {'days': balance, 'hours': balance * daily_hours}
                return {'days': cal_days, 'hours': cal_days * daily_hours}
            return {'days': 0, 'hours': 0}
        return super()._get_number_of_days(date_from, date_to, employee_id)

    # ==================================================================
    # Vacation Return Confirmation
    # ==================================================================

    x_return_date = fields.Date(
        string='Return Date',
        tracking=True,
        help='The actual date the employee returned from annual vacation.',
    )
    x_return_state = fields.Selection([
        ('not_applicable', 'N/A'),
        ('on_vacation', 'On Vacation'),
        ('manager_confirmed', 'Manager Confirmed'),
        ('hr_confirmed', 'Return Confirmed'),
    ], string='Return Status', default='not_applicable',
        tracking=True, copy=False,
    )
    x_manager_return_confirmed_by = fields.Many2one(
        'hr.employee', string='Manager Confirmed By',
        readonly=True, copy=False,
    )
    x_manager_return_date = fields.Datetime(
        string='Manager Confirmed On',
        readonly=True, copy=False,
    )
    x_hr_return_confirmed_by = fields.Many2one(
        'hr.employee', string='HR Confirmed By',
        readonly=True, copy=False,
    )
    x_hr_return_date = fields.Datetime(
        string='HR Confirmed On',
        readonly=True, copy=False,
    )
    x_is_on_vacation = fields.Boolean(
        string='Currently On Vacation',
        compute='_compute_is_on_vacation',
        store=True,
    )
    x_can_confirm_return_manager = fields.Boolean(
        compute='_compute_return_permissions',
    )
    x_can_confirm_return_hr = fields.Boolean(
        compute='_compute_return_permissions',
    )

    @api.depends('state', 'x_return_state')
    def _compute_is_on_vacation(self):
        for leave in self:
            leave.x_is_on_vacation = (
                leave.state == 'validate'
                and leave.x_return_state == 'on_vacation'
            )

    @api.depends_context('uid')
    @api.depends('state', 'x_return_state', 'x_return_date')
    def _compute_return_permissions(self):
        is_hr_officer = self.env.user.has_group(
            'hr_holidays.group_hr_holidays_user')
        for leave in self:
            leave.x_can_confirm_return_manager = (
                leave.state == 'validate'
                and leave.x_return_state == 'on_vacation'
                and leave.x_return_date
            )
            leave.x_can_confirm_return_hr = (
                leave.state == 'validate'
                and leave.x_return_state == 'manager_confirmed'
                and is_hr_officer
            )

    def action_confirm_return_manager(self):
        for leave in self:
            if leave.x_return_state != 'on_vacation':
                raise UserError('This leave is not in "On Vacation" status.')
            if not leave.x_return_date:
                raise UserError(
                    'Please set the Return Date before confirming.')
            leave.write({
                'x_return_state': 'manager_confirmed',
                'x_manager_return_confirmed_by':
                    self.env.user.employee_id.id,
                'x_manager_return_date': fields.Datetime.now(),
            })
            leave.message_post(
                body=Markup(
                    '<strong>📋 Return Confirmed by Manager</strong><br/>'
                    '<b>Employee:</b> %(employee)s<br/>'
                    '<b>Return Date:</b> %(return_date)s<br/>'
                    '<b>Confirmed by:</b> %(confirmer)s'
                ) % {
                    'employee': leave.employee_id.name,
                    'return_date': leave.x_return_date,
                    'confirmer': self.env.user.name,
                },
                subtype_xmlid='mail.mt_note',
            )

    def action_confirm_return_hr(self):
        for leave in self:
            if leave.x_return_state != 'manager_confirmed':
                raise UserError(
                    'Manager confirmation is required before HR '
                    'confirmation.')
            leave.write({
                'x_return_state': 'hr_confirmed',
                'x_hr_return_confirmed_by': self.env.user.employee_id.id,
                'x_hr_return_date': fields.Datetime.now(),
            })
            leave.message_post(
                body=Markup(
                    '<strong>✅ Return Confirmed by HR</strong><br/>'
                    '<b>Employee:</b> %(employee)s<br/>'
                    '<b>Return Date:</b> %(return_date)s<br/>'
                    '<b>Manager Confirmed by:</b> %(manager)s<br/>'
                    '<b>HR Confirmed by:</b> %(hr)s'
                ) % {
                    'employee': leave.employee_id.name,
                    'return_date': leave.x_return_date,
                    'manager':
                        leave.x_manager_return_confirmed_by.name or '',
                    'hr': self.env.user.name,
                },
                subtype_xmlid='mail.mt_note',
            )

    # ==================================================================
    # Multi-Step Approval: can_approve / can_validate overrides
    # ==================================================================

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        """Hide the standard 'Approve' button for annual_multi leaves."""
        annual_multi = self.filtered(self._is_annual_multi)
        remaining = self - annual_multi
        if remaining:
            super(HrLeave, remaining)._compute_can_approve()
        for leave in annual_multi:
            leave.can_approve = False

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_validate(self):
        """Hide the standard 'Validate' button for annual_multi leaves."""
        annual_multi = self.filtered(self._is_annual_multi)
        remaining = self - annual_multi
        if remaining:
            super(HrLeave, remaining)._compute_can_validate()
        for leave in annual_multi:
            leave.can_validate = False

    # ==================================================================
    # Multi-Step Approval: create hook
    # ==================================================================

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for leave in records:
            if self._is_annual_multi(leave):
                leave.sudo().write({
                    'x_annual_approval_state': 'pending_dm',
                })
        return records

    # ==================================================================
    # Multi-Step Approval: action_approve intercept
    # ==================================================================

    def action_approve(self, check_state=True):
        """Intercept annual_multi leaves — route through multi-step."""
        annual_multi = self.filtered(self._is_annual_multi)
        remaining = self - annual_multi

        if annual_multi:
            for leave in annual_multi:
                if leave.x_annual_approval_state == 'pending_dm':
                    leave.action_dm_approve()

        if remaining:
            return super(HrLeave, remaining).action_approve(
                check_state=check_state)
        return True

    # ==================================================================
    # Multi-Step Approval: Step-by-step action methods
    # ==================================================================

    def action_dm_approve(self):
        """Step 1: Direct Manager approves the initial request."""
        for leave in self:
            if leave.x_annual_approval_state != 'pending_dm':
                raise UserError(
                    'This leave is not pending DM approval.')
            # Check that current user is the leave manager or HR
            if (leave.employee_id.leave_manager_id
                    and leave.employee_id.leave_manager_id != self.env.user
                    and not self.env.user.has_group(
                        'hr_holidays.group_hr_holidays_user')):
                raise UserError(
                    'Only %s (the leave manager) or an HR officer '
                    'can approve this step.'
                    % leave.employee_id.leave_manager_id.name
                )
            leave.write({
                'x_annual_approval_state': 'pending_hr',
                'x_dm_approved_by': self.env.user.employee_id.id,
                'x_dm_approved_date': fields.Datetime.now(),
            })
            leave.message_post(
                body=Markup(
                    '<strong>✅ Step 1 — DM Approval</strong><br/>'
                    '<b>Approved by:</b> %(approver)s<br/>'
                    '<b>Employee:</b> %(employee)s<br/>'
                    '<b>Leave Period:</b> %(date_from)s → %(date_to)s'
                    '<br/><b>Days:</b> %(days)s'
                ) % {
                    'approver': self.env.user.name,
                    'employee': leave.employee_id.name,
                    'date_from': leave.request_date_from,
                    'date_to': leave.request_date_to,
                    'days': leave.number_of_days,
                },
                subtype_xmlid='mail.mt_note',
            )

    def action_hr_approve(self):
        """Step 2: HR approves and fills penalty + iqama renewal."""
        self._check_group(
            'hr_holidays.group_hr_holidays_user',
            'Only HR officers can approve this step.',
        )
        for leave in self:
            if leave.x_annual_approval_state != 'pending_hr':
                raise UserError(
                    'This leave is not pending HR approval.')
            leave.write({
                'x_annual_approval_state': 'pending_gm_initial',
                'x_hr_approved_by': self.env.user.employee_id.id,
                'x_hr_approved_date': fields.Datetime.now(),
            })
            body_parts = [
                '<strong>✅ Step 2 — HR Approval</strong><br/>',
                '<b>Approved by:</b> %s<br/>' % self.env.user.name,
            ]
            if leave.x_penalty_amount:
                body_parts.append(
                    '<b>Penalty:</b> %.2f SAR' % leave.x_penalty_amount)
                if leave.x_penalty_description:
                    body_parts.append(
                        ' — %s' % leave.x_penalty_description)
                body_parts.append('<br/>')
            if leave.x_iqama_renewal_amount:
                body_parts.append(
                    '<b>Iqama Renewal:</b> %.2f SAR'
                    % leave.x_iqama_renewal_amount)
                if leave.x_iqama_renewal_description:
                    body_parts.append(
                        ' — %s' % leave.x_iqama_renewal_description)
                body_parts.append('<br/>')
            leave.message_post(
                body=Markup(''.join(body_parts)),
                subtype_xmlid='mail.mt_note',
            )

    def action_gm_initial_approve(self):
        """Step 3: GM gives initial approval (read-only review)."""
        self._check_group(
            'KSW_annual_leave.group_annual_leave_gm',
            'Only the General Manager can approve this step.',
        )
        for leave in self:
            if leave.x_annual_approval_state != 'pending_gm_initial':
                raise UserError(
                    'This leave is not pending GM initial approval.')
            leave.write({
                'x_annual_approval_state': 'pending_acc',
                'x_gm_initial_approved_by':
                    self.env.user.employee_id.id,
                'x_gm_initial_approved_date': fields.Datetime.now(),
            })
            leave.message_post(
                body=Markup(
                    '<strong>✅ Step 3 — GM Initial Approval</strong>'
                    '<br/><b>Approved by:</b> %(approver)s'
                ) % {'approver': self.env.user.name},
                subtype_xmlid='mail.mt_note',
            )

    def action_acc_approve(self):
        """Step 4: Accounting approves and fills flight ticket."""
        self._check_group(
            'KSW_annual_leave.group_annual_leave_acc',
            'Only Accounting Approvers can approve this step.',
        )
        for leave in self:
            if leave.x_annual_approval_state != 'pending_acc':
                raise UserError(
                    'This leave is not pending accounting approval.')
            leave.write({
                'x_annual_approval_state': 'pending_gm_final',
                'x_acc_approved_by': self.env.user.employee_id.id,
                'x_acc_approved_date': fields.Datetime.now(),
            })
            body_parts = [
                '<strong>✅ Step 4 — Accounting Approval</strong><br/>',
                '<b>Approved by:</b> %s<br/>' % self.env.user.name,
            ]
            if leave.x_flight_ticket_amount:
                body_parts.append(
                    '<b>Flight Ticket:</b> %.2f SAR'
                    % leave.x_flight_ticket_amount)
                if leave.x_flight_ticket_description:
                    body_parts.append(
                        ' — %s' % leave.x_flight_ticket_description)
                body_parts.append('<br/>')
            leave.message_post(
                body=Markup(''.join(body_parts)),
                subtype_xmlid='mail.mt_note',
            )

    def action_gm_final_approve(self):
        """Step 5: GM gives final approval.

        Creates vacation payslip, then triggers Odoo validation
        (state → validate, allocation deducted, on-vacation flag).
        """
        self._check_group(
            'KSW_annual_leave.group_annual_leave_gm',
            'Only the General Manager can give final approval.',
        )
        for leave in self:
            if leave.x_annual_approval_state != 'pending_gm_final':
                raise UserError(
                    'This leave is not pending GM final approval.')

            leave.write({
                'x_annual_approval_state': 'approved',
                'x_gm_final_approved_by':
                    self.env.user.employee_id.id,
                'x_gm_final_approved_date': fields.Datetime.now(),
            })

            # Create vacation payslip BEFORE _action_validate
            # (_action_validate sets x_return_state='on_vacation'
            #  which would trigger the vacation-return guard).
            leave._create_vacation_payslip()

            leave.message_post(
                body=Markup(
                    '<strong>✅ Step 5 — GM Final Approval</strong>'
                    '<br/><b>Approved by:</b> %(approver)s<br/>'
                    '<b>Status:</b> Fully approved.'
                ) % {'approver': self.env.user.name},
                subtype_xmlid='mail.mt_note',
            )

        # Standard Odoo validation: state → 'validate'
        self._action_validate(check_state=False)

    # ==================================================================
    # Vacation payslip hook (overridden by KSW_payroll)
    # ==================================================================

    def _create_vacation_payslip(self):
        """Hook for KSW_payroll to create a vacation payslip.

        Base implementation does nothing. KSW_payroll overrides this
        to create an actual payslip with vacation inputs.
        """
        pass

    # ==================================================================
    # Helpers
    # ==================================================================

    def _check_group(self, group_xmlid, message):
        """Raise UserError if current user doesn't belong to the group."""
        if not self.env.user.has_group(group_xmlid):
            raise UserError(message)

    def _reset_annual_multi_fields(self):
        """Reset all multi-step approval fields to their defaults."""
        self.write({
            'x_annual_approval_state': False,
            'x_penalty_amount': 0,
            'x_penalty_description': False,
            'x_iqama_renewal_amount': 0,
            'x_iqama_renewal_description': False,
            'x_flight_ticket_amount': 0,
            'x_flight_ticket_description': False,
            'x_dm_approved_by': False,
            'x_dm_approved_date': False,
            'x_hr_approved_by': False,
            'x_hr_approved_date': False,
            'x_gm_initial_approved_by': False,
            'x_gm_initial_approved_date': False,
            'x_acc_approved_by': False,
            'x_acc_approved_date': False,
            'x_gm_final_approved_by': False,
            'x_gm_final_approved_date': False,
        })

    # ==================================================================
    # Override _action_validate — set return state on vacation
    # ==================================================================

    def _action_validate(self, check_state=True):
        """Set return state to 'on_vacation' when annual leave validated."""
        result = super()._action_validate(check_state=check_state)
        annual = self.filtered(self._is_annual_leave)
        if annual:
            annual.write({'x_return_state': 'on_vacation'})
            # Refresh accrual — leaves_taken changed (leave now validated)
            emp_ids = annual.mapped('employee_id').ids
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(emp_ids)
        return result

    # ==================================================================
    # Override action_refuse — reset multi-step fields
    # ==================================================================

    def _move_validate_leave_to_confirm(self):
        """Override 'Back to Approval' to reset multi-step approval,
        return state, and restart the approval chain."""
        annual = self.filtered(
            lambda l: self._is_annual_leave(l)
            and l.x_return_state != 'not_applicable'
        )
        annual_multi = self.filtered(self._is_annual_multi)

        # Collect employee IDs before state changes
        annual_emp_ids = self.filtered(self._is_annual_leave).mapped('employee_id').ids

        if annual:
            annual.write({
                'x_return_state': 'not_applicable',
                'x_return_date': False,
                'x_manager_return_confirmed_by': False,
                'x_manager_return_date': False,
                'x_hr_return_confirmed_by': False,
                'x_hr_return_date': False,
            })

        if annual_multi:
            annual_multi._reset_annual_multi_fields()

        result = super()._move_validate_leave_to_confirm()

        # After super sets state='confirm', restart the approval chain
        if annual_multi:
            annual_multi.write({'x_annual_approval_state': 'pending_dm'})

        # Refresh accrual — leaves_taken changed
        if annual_emp_ids:
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(annual_emp_ids)

        return result

    def action_refuse(self):
        """Reset return and multi-step fields when refused."""
        annual = self.filtered(
            lambda l: self._is_annual_leave(l)
            and l.x_return_state != 'not_applicable'
        )
        annual_multi = self.filtered(self._is_annual_multi)

        # Collect employee IDs before state changes
        annual_emp_ids = self.filtered(self._is_annual_leave).mapped('employee_id').ids

        result = super().action_refuse()

        if annual:
            annual.write({
                'x_return_state': 'not_applicable',
                'x_return_date': False,
                'x_manager_return_confirmed_by': False,
                'x_manager_return_date': False,
                'x_hr_return_confirmed_by': False,
                'x_hr_return_date': False,
            })

        if annual_multi:
            annual_multi._reset_annual_multi_fields()
            # Vacation payslip cancellation handled by KSW_payroll override

        # Refresh accrual — leaves_taken changed (leave no longer validated)
        if annual_emp_ids:
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(annual_emp_ids)

        return result

    # ==================================================================
    # Override action_draft — restart multi-step chain
    # ==================================================================

    def action_draft(self):
        """When resetting to draft, restart the approval chain."""
        # Collect employee IDs before state changes
        annual_emp_ids = self.filtered(self._is_annual_leave).mapped('employee_id').ids

        result = super().action_draft()
        annual_multi = self.filtered(self._is_annual_multi)
        if annual_multi:
            annual_multi._reset_annual_multi_fields()
            for leave in annual_multi:
                leave.x_annual_approval_state = 'pending_dm'
            # Vacation payslip cancellation handled by KSW_payroll override

        # Refresh accrual — leaves_taken changed
        if annual_emp_ids:
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(annual_emp_ids)

        return result

    # ==================================================================
    # Override unlink — refresh accrual when annual leave is deleted
    # ==================================================================

    def unlink(self):
        """Refresh accrual when an annual leave record is deleted."""
        annual = self.filtered(self._is_annual_leave)
        annual_emp_ids = annual.mapped('employee_id').ids
        result = super().unlink()
        if annual_emp_ids:
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(annual_emp_ids)
        return result
