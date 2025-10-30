# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AttendanceChangeProjectWizard(models.TransientModel):
    _name = 'attendance.change.project.wizard'
    _description = 'Change Project During Work'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Attendance',
        required=True,
        readonly=True,
    )
    current_project_id = fields.Many2one(
        'project.project',
        string='Current Project',
        readonly=True,
    )
    new_project_id = fields.Many2one(
        'project.project',
        string='New Project',
        required=True,
        domain="[('allow_timesheets', '=', True)]",
    )
    employee_id = fields.Many2one(
        'hr.employee',
        related='attendance_id.employee_id',
        string='Employee',
    )

    def action_change_project(self):
        """Execute project change"""
        self.ensure_one()

        if not self.new_project_id:
            raise UserError(_("Please select a new project."))

        if self.new_project_id == self.current_project_id:
            raise UserError(_("New project is the same as current project."))

        # Execute the change
        self.attendance_id.change_project_to(self.new_project_id.id)

        return {'type': 'ir.actions.act_window_close'}

    def action_checkout(self):
        """Check out and close timesheets"""
        self.ensure_one()

        # Perform check-out
        self.attendance_id.write({
            'check_out': fields.Datetime.now(),
        })

        return {'type': 'ir.actions.act_window_close'}
