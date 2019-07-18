# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeBase(models.AbstractModel):
    _name = "hr.employee.base"
    _description = "Basic Employee"
    _order = 'name'

    name = fields.Char()
    active = fields.Boolean("Active")
    color = fields.Integer('Color Index', default=0)
    department_id = fields.Many2one('hr.department', 'Department')
    job_id = fields.Many2one('hr.job', 'Job Position')
    job_title = fields.Char("Job Title")
    company_id = fields.Many2one('res.company', 'Company')
    address_id = fields.Many2one('res.partner', 'Work Address')
    work_phone = fields.Char('Work Phone')
    mobile_phone = fields.Char('Work Mobile')
    work_email = fields.Char('Work Email')
    work_location = fields.Char('Work Location')
    user_id = fields.Many2one('res.users')
    resource_id = fields.Many2one('resource.resource')
    resource_calendar_id = fields.Many2one('resource.calendar')
