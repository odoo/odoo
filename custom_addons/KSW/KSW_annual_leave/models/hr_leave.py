from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


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

    # --- _compute_duration -------------------------------------------

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

    # --- _get_durations (used by _get_consumed_leaves) ----------------

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

    # --- _get_number_of_days -----------------------------------------

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

    # ------------------------------------------------------------------
    # Vacation Return Confirmation
    # ------------------------------------------------------------------

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
        is_hr_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
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

    # --- Vacation return actions ----------------------------------------

    def action_confirm_return_manager(self):
        """Direct manager confirms the employee has returned from vacation."""
        for leave in self:
            if leave.x_return_state != 'on_vacation':
                raise UserError('This leave is not in "On Vacation" status.')
            if not leave.x_return_date:
                raise UserError('Please set the Return Date before confirming.')

            leave.write({
                'x_return_state': 'manager_confirmed',
                'x_manager_return_confirmed_by': self.env.user.employee_id.id,
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
        """HR officer gives final confirmation that the employee has returned."""
        for leave in self:
            if leave.x_return_state != 'manager_confirmed':
                raise UserError('Manager confirmation is required before HR confirmation.')

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
                    'manager': leave.x_manager_return_confirmed_by.name or '',
                    'hr': self.env.user.name,
                },
                subtype_xmlid='mail.mt_note',
            )

    # --- Hook into leave validation / refuse ----------------------------

    def _action_validate(self, check_state=True):
        """Set return state to 'on_vacation' when annual leave is validated."""
        result = super()._action_validate(check_state=check_state)
        annual = self.filtered(self._is_annual_leave)
        if annual:
            annual.write({'x_return_state': 'on_vacation'})
        return result

    def action_refuse(self):
        """Reset return state when annual leave is refused."""
        annual = self.filtered(
            lambda l: self._is_annual_leave(l) and l.x_return_state != 'not_applicable'
        )
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
        return result
