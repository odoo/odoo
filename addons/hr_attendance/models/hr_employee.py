# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _description = "Employee"

    state = fields.Selection([('absent', 'Absent'), ('present', 'Present')], compute='_state', string='Attendance')
    last_sign = fields.Datetime(compute='_last_sign', string='Last Sign')
    attendance_access = fields.Boolean(compute='_attendance_access', string='Attendance Access')

    @api.multi
    def _state(self):
        self.env.cr.execute('SELECT hr_attendance.action, hr_attendance.employee_id \
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
        for res in self.env.cr.fetchall():
            self.state = 'present' if res[0] == 'sign_in' else 'absent'

    def _last_sign(self):
        self.env.cr.execute("""select max(name) as name
            from hr_attendance
            where action in ('sign_in', 'sign_out') and employee_id = %s""", (self.id,))
        for res in self.env.cr.fetchall():
            self.last_sign = res[0]

    def _attendance_access(self):
        # this function field use to hide attendance button to singin/singout from menu
        self.attendance_access = self.env['res.users'].has_group("base.group_hr_attendance")

    def _action_check(self, dt=False):
        self.env.cr.execute('SELECT MAX(name) FROM hr_attendance WHERE employee_id=%s', (self.id,))
        res = self.env.cr.fetchone()
        return not (res and (res[0] >= (dt or fields.Datetime.now())))

    @api.multi
    def attendance_action_change(self):
        action_date = self.env.context.get('action_date', False)
        action = self.env.context.get('action', False)
        warning_sign = {'sign_in': _('Sign In'), 'sign_out': _('Sign Out')}
        for employee in self:
            if not action:
                action = 'sign_out' if employee.state == 'present' else 'sign_in'
            if not self._action_check(action_date):
                raise UserError(_('You tried to %s with a date anterior to another event !\nTry to contact the HR Manager to correct attendances.') % (warning_sign[action],))

            vals = {'action': action, 'employee_id': employee.id}
            if action_date:
                vals['name'] = action_date
            self.env['hr.attendance'].create(vals)
        return True
