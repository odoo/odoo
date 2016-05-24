# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    @api.depends('timesheet_count')
    def _compute_timesheet_count(self):
        self.timesheet_count = self.env['hr_timesheet_sheet.sheet'].search_count([('employee_id', 'in', self.ids)])

    timesheet_count = fields.Integer(compute='_compute_timesheet_count', string='Timesheets')
