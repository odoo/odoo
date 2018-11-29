# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPlanWizard(models.TransientModel):
    _name = 'hr.plan.wizard'
    _description = 'Plan Wizard'

    plan_id = fields.Many2one('hr.plan', default=lambda self: self.env['hr.plan'].search([], limit=1))

    def launch(self):
        active_id = self.env.context.get('active_id')

        rec = self.env['hr.employee'].browse(active_id)

        for activity_type in self.plan_id.plan_activity_type_ids:
            self.env['mail.activity'].create({
                'res_id': rec.id,
                'res_model_id': self.env['ir.model']._get('hr.employee').id,
                'activity_type_id': activity_type.activity_type_id.id,
                'user_id': activity_type.get_responsible_id(rec).id,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': active_id,
            'name': rec.display_name,
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(False, "form")],
        }
