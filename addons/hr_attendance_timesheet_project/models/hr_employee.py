# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    last_project_id = fields.Many2one(
        'project.project',
        string='Last Project',
        domain="[('allow_timesheets', '=', True)]",
        help="Last project this employee worked on. Used as default for next check-in."
    )

    default_project_id = fields.Many2one(
        'project.project',
        string='Default Project',
        domain="[('allow_timesheets', '=', True)]",
        help="Default project for this employee if no last project is set"
    )

    @api.model
    def _get_employee_default_project(self, employee_id):
        """Get the default project for an employee"""
        employee = self.browse(employee_id)

        # Priority: last_project_id > default_project_id > company default
        if employee.last_project_id:
            return employee.last_project_id

        if employee.default_project_id:
            return employee.default_project_id

        # Fallback to default project '0 - Koszty Stałe'
        return self.env.ref('hr_attendance_timesheet_project.project_koszty_stale', raise_if_not_found=False)
