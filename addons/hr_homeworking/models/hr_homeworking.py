# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

DAYS = ['monday_location_id', 'tuesday_location_id', 'wednesday_location_id', 'thursday_location_id', 'friday_location_id', 'saturday_location_id', 'sunday_location_id']


class HrEmployeeLocation(models.Model):
    _name = "hr.employee.location"
    _description = "Employee Location"

    work_location_id = fields.Many2one('hr.work.location', required=True, string="Location")
    work_location_name = fields.Char(related='work_location_id.name', string="Location name")
    work_location_type = fields.Selection(related="work_location_id.location_type")
    employee_id = fields.Many2one('hr.employee', default=lambda self: self.env.user.employee_id, required=True, ondelete="cascade")
    employee_name = fields.Char(related="employee_id.name")
    date = fields.Date(string="Date")
    day_week_string = fields.Char(compute="_compute_day_week_string")

    _sql_constraints = [
        ('uniq_exceptional_per_day', 'unique(employee_id, date)', 'Only one default work location and one exceptional work location per day per employee.'),
    ]

    @api.depends('date')
    def _compute_day_week_string(self):
        for record in self:
            record.day_week_string = record.date.strftime("%A")
