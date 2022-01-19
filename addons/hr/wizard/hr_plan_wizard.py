# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrPlanWizard(models.TransientModel):
    _name = 'hr.plan.wizard'
    _description = 'Plan Wizard'

    def _default_plan_id(self):
        employee = self.env['hr.employee'].browse(self.env.context.get('active_id'))
        return self.env['hr.plan'].search([('company_id', '=', employee.company_id.id)], limit=1)

    plan_id = fields.Many2one('hr.plan', default=_default_plan_id, domain="[('company_id', '=', company_id)]")
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        default=lambda self: self.env.context.get('active_id', None),
    )
    company_id = fields.Many2one(related='employee_id.company_id')

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

        for plan in self:
            plan.employee_id.message_post(body=_('The plan %s has been started', plan.plan_id.name))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'name': self.employee_id.display_name,
            'view_mode': 'form',
            'views': [(False, "form")],
        }
