
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import api, fields, models


class HrLeaveMandatoryDay(models.Model):
    _name = 'hr.leave.mandatory.day'
    _description = 'Mandatory Day'
    _order = 'start_date desc, end_date desc'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    color = fields.Integer(default=lambda dummy: randint(1, 11))
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    departments_for_job_domain = fields.Many2many('hr.department', compute='_compute_department_domain')
    department_ids = fields.Many2many('hr.department', string="Departments")
    job_ids = fields.Many2many('hr.job', string="Job Position", domain="[('department_id', 'in', departments_for_job_domain)]")

    _date_from_after_day_to = models.Constraint(
        'CHECK(start_date <= end_date)',
        'The start date must be anterior than the end date.',
    )

    @api.depends('job_ids', 'department_ids')
    def _compute_department_domain(self):
        all_departments = self.env['hr.department'].search([])
        for mandatory_day in self:
            mandatory_day.departments_for_job_domain = mandatory_day.department_ids or all_departments
