# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import fields, models


class StressDay(models.Model):
    _name = 'hr.leave.stress.day'
    _description = 'Stress Day'
    _order = 'start_date desc, end_date desc'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    color = fields.Integer(default=lambda dummy: randint(1, 11))
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    department_ids = fields.Many2many('hr.department', string="Departments")

    _sql_constraints = [
        ('date_from_after_day_to', 'CHECK(start_date <= end_date)', 'The start date must be anterior than the end date.')
    ]
