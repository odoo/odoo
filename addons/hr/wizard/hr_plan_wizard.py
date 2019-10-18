# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPlanWizard(models.TransientModel):
    _name = 'hr.plan.wizard'
    _description = 'Plan Wizard'

    @api.model
    def default_get(self, fields_list):
        res = super(HrPlanWizard, self).default_get(fields_list)
        if (not fields_list or 'employee_id' in fields_list) and 'employee_id' not in res:
            if self.env.context.get('active_id'):
                res['employee_id'] = self.env.context['active_id']
        return res

    plan_id = fields.Many2one('hr.plan', default=lambda self: self.env['hr.plan'].search([], limit=1))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)

    def action_launch(self):
        for activity_type in self.plan_id.plan_activity_type_ids:
            responsible = activity_type.get_responsible_id(self.employee_id)

            if self.env['hr.employee'].with_user(responsible).check_access_rights('read', raise_exception=False):
                self.env['mail.activity'].create({
                    'res_id': self.employee_id.id,
                    'res_model_id': self.env['ir.model']._get('hr.employee').id,
                    'summary': activity_type.summary,
                    'note': activity_type.note,
                    'activity_type_id': activity_type.activity_type_id.id,
                    'user_id': responsible.id,
                })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'name': self.employee_id.display_name,
            'view_mode': 'form',
            'views': [(False, "form")],
        }
