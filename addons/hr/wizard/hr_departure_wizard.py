# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrDepartureWizard(models.TransientModel):
    _name = 'hr.departure.wizard'
    _description = 'Departure Wizard'

    @api.model
    def default_get(self, fields):
        res = super(HrDepartureWizard, self).default_get(fields)
        if (not fields or 'employee_id' in fields) and 'employee_id' not in res:
            if self.env.context.get('active_id'):
                res['employee_id'] = self.env.context['active_id']
        return res

    departure_reason = fields.Selection([
        ('fired', 'Fired'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired')
    ], string="Departure Reason", default="fired")
    departure_description = fields.Text(string="Additional Information")
    plan_id = fields.Many2one('hr.plan', default=lambda self: self.env['hr.plan'].search([], limit=1))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)

    def action_register_departure(self):
        employee = self.employee_id
        employee.departure_reason = self.departure_reason
        employee.departure_description = self.departure_description

        for activity_type in self.plan_id.plan_activity_type_ids:
            self.env['mail.activity'].create({
                'res_id': employee.id,
                'res_model_id': self.env['ir.model']._get('hr.employee').id,
                'activity_type_id': activity_type.activity_type_id.id,
                'summary': activity_type.summary,
                'user_id': activity_type.get_responsible_id(employee).id,
            })
