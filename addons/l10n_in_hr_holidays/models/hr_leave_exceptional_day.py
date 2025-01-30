# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrHolidayExceptionalDay(models.Model):
    _name = 'l10n.in.hr.holiday.exceptional.day'
    _description = 'Exceptional Day'
    _order = 'start_date desc, end_date desc'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    color = fields.Integer(default=lambda dummy: randint(1, 11))
    department_ids = fields.Many2many('hr.department', string="Departments")
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    _date_from_after_day_to = models.Constraint(
        'CHECK(start_date <= end_date)',
        'The start date must be anterior than the end date.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            public_leave = self.env['resource.calendar.leaves'].search([
                ('time_type', '=', 'leave'),
                ('date_from', '<=', fields.Datetime.to_datetime(vals['end_date'])),
                ('date_to', '>=', fields.Datetime.to_datetime(vals['start_date'])),
                ('company_id', '=', vals.get('company_id'))
            ])
            if public_leave:
                raise UserError(_('You cannot create an exceptional day that overlaps with a public leave.'))
            return super().create(vals_list)
