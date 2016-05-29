# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class HrActionReason(models.Model):
    _name = "hr.action.reason"
    _description = "Action Reason"

    name = fields.Char(string='Reason', required=True, help='Specifies the reason for Signing In/Signing Out.')
    action_type = fields.Selection([('sign_in', 'Sign in'), ('sign_out', 'Sign out')], default='sign_in')


class HrAttendance(models.Model):
    _name = "hr.attendance"
    _description = "Attendance"
    _order = 'name desc'

    def _employee_get(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Datetime(string='Date', required=True, index=True, default=fields.Datetime.now)
    action = fields.Selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('action', 'Action')], required=True)
    action_desc = fields.Many2one("hr.action.reason", string="Action Reason", domain="[('action_type', '=', action)]", help='Specifies the reason for Signing In/Signing Out in case of extra hours.')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, index=True, default=_employee_get)
    department_id = fields.Many2one('hr.department', related="employee_id.department_id")
    worked_hours = fields.Float(compute='_compute_worked_hours', store=True)

    @api.depends('employee_id', 'name', 'action')
    def _compute_worked_hours(self):
        """For each hr.attendance record of action sign-in: assign 0.
        For each hr.attendance record of action sign-out: assign number of hours since last sign-in.
        """
        for attendance in self:
            if attendance.action == 'sign_in':
                attendance.worked_hours = 0
            elif attendance.action == 'sign_out':
                # Get the associated sign-in
                last_signin = self.search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('name', '<', attendance.name), ('action', '=', 'sign_in')],
                    limit=1, order='name DESC')
                if last_signin:
                    # Compute time elapsed between sign-in and sign-out
                    last_signin_datetime = fields.Datetime.from_string(last_signin.name)
                    signout_datetime = fields.Datetime.from_string(attendance.name)
                    workedhours_datetime = (signout_datetime - last_signin_datetime)
                    attendance.worked_hours = ((workedhours_datetime.seconds) / 60) / 60.0
                else:
                    attendance.worked_hours = False

    @api.constrains('action')
    def _check_altern_si_so(self):
        """ Alternance sign_in/sign_out check.
            Previous (if exists) must be of opposite action.
            Next (if exists) must be of opposite action.
        """
        for attendance in self:
            # search first previous and first next records
            prev_attendance = self.search([('employee_id', '=', attendance.employee_id.id), ('name', '<', attendance.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name DESC')
            next_attendance = self.search([('employee_id', '=', attendance.employee_id.id), ('name', '>', attendance.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name ASC')
            msg = _('Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)')
            # check for alternance, raise ValidationError if at least one condition is not satisfied
            if prev_attendance.action == attendance.action: # previous exists and is same action
                raise ValidationError(msg)
            if next_attendance.action == attendance.action: # next exists and is same action
                raise ValidationError(msg)
            if (not prev_attendance) and (not next_attendance) and attendance.action != 'sign_in': # first attendance must be sign_in
                raise ValidationError(_("Error ! First action must be Sign in"))


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _description = "Employee"

    state = fields.Selection([('absent', 'Absent'), ('present', 'Present')], compute='_compute_state', string='Attendance')
    last_sign = fields.Datetime(compute='_compute_last_sign', string='Last Sign')
    attendance_access = fields.Boolean(compute='_compute_attendance_access', string='Attendance Access')

    def _compute_state(self):
        self.env.cr.execute('SELECT hr_attendance.employee_id, hr_attendance.action \
                FROM ( \
                    SELECT MAX(name) AS name, employee_id \
                    FROM hr_attendance \
                    WHERE action in (\'sign_in\', \'sign_out\') \
                    GROUP BY employee_id \
                ) AS foo \
                LEFT JOIN hr_attendance \
                    ON (hr_attendance.employee_id = foo.employee_id \
                        AND hr_attendance.name = foo.name) \
                WHERE hr_attendance.employee_id IN %s', (tuple(self.ids),))
        res = dict(self.env.cr.fetchall())

        for employee in self:
            employee.state = 'present' if res.get(employee.id) == 'sign_in' else 'absent'

    def _compute_last_sign(self):
        for employee in self:
            self.env.cr.execute("""select max(name) as name
                        from hr_attendance
                        where action in ('sign_in', 'sign_out') and employee_id = %s""",(employee.id,))
            for res in self.env.cr.fetchall():
                employee.last_sign = res[0]

    def _compute_attendance_access(self):
        # this function field use to hide attendance button to sign_in/sign_out from menu
        access = self.env.user.has_group("base.group_hr_attendance")
        for employee in self:
            employee.attendance_access = access

    def _action_check(self, dt=False):
        self.env.cr.execute('SELECT MAX(name) FROM hr_attendance WHERE employee_id=%s', (self.id,))
        res = self.env.cr.fetchone()
        return not (res and (res[0] >= (dt or fields.Datetime.now())))

    @api.multi
    def attendance_action_change(self):
        action_date = self.env.context.get('action_date')
        action = self.env.context.get('action')
        warning_sign = {'sign_in': _('Sign In'), 'sign_out': _('Sign Out')}
        for employee in self:
            if not action:
                action = 'sign_out' if employee.state == 'present' else 'sign_in'

            if not employee._action_check(action_date):
                raise UserError(_('You tried to %s with a date anterior to another event !\nTry to contact the HR Manager to correct attendances.') % (warning_sign[action],))

            vals = {'action': action, 'employee_id': employee.id}
            if action_date:
                vals['name'] = action_date
            self.env['hr.attendance'].create(vals)
        return True
