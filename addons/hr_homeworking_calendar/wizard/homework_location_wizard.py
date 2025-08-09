# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

from odoo.addons.hr_homeworking.models.hr_homeworking import DAYS

class HomeworkLocationWizard(models.TransientModel):
    _name = 'homework.location.wizard'
    _description = 'Set Homework Location Wizard'

    work_location_id = fields.Many2one('hr.work.location', required=True, string="Location")
    work_location_name = fields.Char(related='work_location_id.name', string="Location name")
    work_location_type = fields.Selection(related="work_location_id.location_type")
    employee_id = fields.Many2one('hr.employee', default=lambda self: self.env.user.employee_id, required=True, ondelete="cascade")
    employee_name = fields.Char(related="employee_id.name")
    user_can_edit = fields.Boolean(compute='_compute_user_can_edit')
    weekly = fields.Boolean(default=False)
    date = fields.Date(string="Date")
    day_week_string = fields.Char(compute="_compute_day_week_string")

    @api.depends('date')
    def _compute_day_week_string(self):
        for record in self:
            record.day_week_string = record.date.strftime("%A") if record.date else ''

    @api.depends('date')
    def _compute_user_can_edit(self):
        self.user_can_edit = self.env.user.can_edit

    def set_employee_location(self):
        self.ensure_one()
        if not self.date:
            return
        default_employee_id = self.env.context.get('default_employee_id') or self.env.user.employee_id.id
        employee_id = self.env['hr.employee'].browse(self.employee_id.id or default_employee_id)
        employee_location = self.env['hr.employee.location'].search([
            ('date', '=', self.date),
            ('employee_id', '=', employee_id.id)
        ])
        weekday = self.date.weekday()
        default_location_for_current_date = DAYS[weekday]
        if self.weekly:
            # delete any exceptions on the current date
            if employee_location:
                employee_location.unlink()
            employee_id.sudo().user_id.write({
                default_location_for_current_date: self.work_location_id.id,
            })
        else:
            # check if work_location_id is the same as the default one for that day
            if self.work_location_id.id == employee_id[default_location_for_current_date].id:
                employee_location.unlink()
            # check if worklocation is set for that employee that day
            elif employee_location:
                employee_location.write({
                    'date': self.date,
                    'employee_id': employee_id.id,
                    'work_location_id': self.work_location_id.id
                })
            else:
                self.env['hr.employee.location'].create({
                    'date': self.date,
                    'employee_id': employee_id.id,
                    'work_location_id': self.work_location_id.id
                })
