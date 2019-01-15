# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrDepartureWizard(models.TransientModel):
    _name = 'hr.departure.wizard'
    _description = 'Departure Wizard'

    departure_reason = fields.Selection([
        ('fired', 'Fired'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired')
    ], string="Departure Reason", default="fired")
    departure_description = fields.Text(string="Additional Information")
    plan_id = fields.Many2one('hr.plan', default=lambda self: self.env['hr.plan'].search([], limit=1))

    def action_register_departure(self):
        active_id = self.env.context.get('active_id')

        employee = self.env['hr.employee'].browse(active_id)
        employee.departure_reason = self.departure_reason
        employee.departure_description = self.departure_description

        for activity_type in self.plan_id.plan_activity_type_ids:
            self.env['mail.activity'].create({
                'res_id': employee.id,
                'res_model_id': self.env['ir.model']._get('hr.employee').id,
                'activity_type_id': activity_type.activity_type_id.id,
                'user_id': activity_type.get_responsible_id(employee).id,
            })
