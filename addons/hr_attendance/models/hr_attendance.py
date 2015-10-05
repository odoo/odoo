# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrActionReason(models.Model):
    _name = "hr.action.reason"
    _description = "Action Reason"
    name = fields.Char('Reason', required=True, help='Specifies the reason for Signing In/Signing Out.')
    action_type = fields.Selection([('sign_in', 'Sign in'), ('sign_out', 'Sign out')], default='sign_in')

class HrAttendance(models.Model):
    _name = "hr.attendance"
    _description = "Attendance"
    _order = 'name desc'

    def _employee_get(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).id or False

    name = fields.Datetime('Date', required=True, select=1, default=lambda self: fields.datetime.now())
    action = fields.Selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('action', 'Action')], required=True)
    action_desc = fields.Many2one("hr.action.reason", "Action Reason", domain="[('action_type', '=', action)]", help='Specifies the reason for Signing In/Signing Out in case of extra hours.')
    employee_id = fields.Many2one('hr.employee', "Employee", required=True, select=True, default=_employee_get)
    department_id = fields.Many2one('hr.department', "Department", related="employee_id.department_id")
    worked_hours = fields.Float(compute='_worked_hours_compute', store=True)

    @api.depends('employee_id', 'name', 'action')
    def _worked_hours_compute(self):
        """For each hr.attendance record of action sign-in: assign 0.
        For each hr.attendance record of action sign-out: assign number of hours since last sign-in.
        """
        for attend in self:
            if attend.action == 'sign_in':
                attend.worked_hours = 0
            elif attend.action == 'sign_out':
                # Get the associated sign-in
                last_signin = self.search([
                    ('employee_id', '=', attend.employee_id.id),
                    ('name', '<', attend.name), ('action', '=', 'sign_in')],
                    limit=1, order='name DESC')
                if last_signin:
                    # Compute time elapsed between sign-in and sign-out
                    workedhours_datetime = (fields.Datetime.from_string(attend.name) - fields.Datetime.from_string(last_signin.name))
                    attend.worked_hours = ((workedhours_datetime.seconds) / 60) / 60.0
                else:
                    attend.worked_hours = False

    @api.constrains('action')
    def _altern_si_so(self):
        """ Alternance sign_in/sign_out check.
            Previous (if exists) must be of opposite action.
            Next (if exists) must be of opposite action.
        """
        for attend in self:
            # search first previous and first next records
            prev_attend = self.search([('employee_id', '=', attend.employee_id.id), ('name', '<', attend.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name DESC')
            next_attend = self.search([('employee_id', '=', attend.employee_id.id), ('name', '>', attend.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name ASC')
            # check for alternance, raise UserError if at least one condition is not satisfied
            if prev_attend and prev_attend.action == attend.action: # previous exists and is same action
                raise UserError(_('Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)'))
            if next_attend and next_attend.action == attend.action: # next exists and is same action
                raise UserError(_('Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)'))
            if (not prev_attend) and (not next_attend) and attend.action != 'sign_in': # first attendance must be sign_in
                raise UserError(_('Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)'))
