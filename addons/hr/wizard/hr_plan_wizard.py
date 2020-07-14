# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPlanWizard(models.TransientModel):
    _name = 'hr.plan.wizard'
    _description = 'Plan Wizard'

    plan_id = fields.Many2one('hr.plan', default=lambda self: self.env['hr.plan'].search([], limit=1))
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        default=lambda self: self.env.context.get('active_id', None),
    )

    def action_launch(self):
        for activity_type in self.plan_id.plan_activity_type_ids:
            responsible = activity_type.get_responsible_id(self.employee_id)

            if self.env['hr.employee'].with_user(responsible).check_access_rights('read', raise_exception=False):
                date_deadline = self.env['mail.activity']._calculate_date_deadline(activity_type.activity_type_id)
                self.employee_id.activity_schedule(
                    activity_type_id=activity_type.activity_type_id.id,
                    summary=activity_type.summary,
                    note=activity_type.note,
                    user_id=responsible.id,
                    date_deadline=date_deadline
                )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'name': self.employee_id.display_name,
            'view_mode': 'form',
            'views': [(False, "form")],
        }
