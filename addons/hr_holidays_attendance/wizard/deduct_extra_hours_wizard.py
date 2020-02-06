# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.resource.models.resource import HOURS_PER_DAY


class DeductExtraHoursWizard(models.TransientModel):
    _name = 'deduct.extra.hours.wizard'
    _description = 'Extra Hours Deduction Wizard'

    def _default_employee(self):
        return self.env['hr.employee'].browse(self._context.get('active_id'))

    def _default_number_of_hours_display(self):
        return self.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY

    description = fields.Char("Description")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, default=_default_employee)
    extra_hours = fields.Float(related='employee_id.extra_hours', readonly=True)
    extra_hours_display = fields.Float(compute="_compute_extra_hours_display")
    leave_type_id = fields.Many2one('hr.leave.type', string="Time Off Type", required=True, domain=[('deduct_from_extra_hours', '=', True)])
    request_unit = fields.Selection(related='leave_type_id.request_unit', readonly=True)
    number_of_days = fields.Float("Number of Days", compute='_compute_number_of_days')
    number_of_days_display = fields.Float("Duration (days)", default=1)
    number_of_hours_display = fields.Float("Duration (hours)", default=_default_number_of_hours_display)

    @api.depends('request_unit')
    def _compute_extra_hours_display(self):
        self.extra_hours_display = self.extra_hours / (self.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY)
        if self.request_unit == 'day':
            self.extra_hours_display = self.extra_hours / (self.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY)
        elif self.request_unit == 'hour':
            self.extra_hours_display = self.extra_hours

    @api.depends('number_of_days_display', 'number_of_hours_display', 'request_unit')
    def _compute_number_of_days(self):
        self.number_of_days = 0
        if self.request_unit == 'day':
            self.number_of_days = self.number_of_days_display
        elif self.request_unit == 'hour':
            self.number_of_days = self.number_of_hours_display / (self.employee_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY)

    def action_request_allocation(self):
        self.env['hr.leave.allocation'].create({
            'name': self.description,
            'state': 'confirm',
            'employee_id': self.employee_id.id,
            'holiday_status_id': self.leave_type_id.id,
            'number_of_days': self.number_of_days,
        })
