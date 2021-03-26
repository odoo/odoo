# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPlanWizard(models.TransientModel):
    _name = 'hr.plan.wizard'
    _description = 'Plan Wizard'

    plan_id = fields.Many2one(
        'hr.plan',
        default=lambda self: self.env['hr.plan'].search([('trigger', '=', 'manual')], limit=1),
        domain="[('trigger', '=', 'manual')]",
        required=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        default=lambda self: self.env.context.get('active_id', None),
    )

    def action_launch(self):
        self.ensure_one()
        self.employee_id._launch_plan(self.plan_id)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'name': self.employee_id.display_name,
            'view_mode': 'form',
            'views': [(False, "form")],
        }
