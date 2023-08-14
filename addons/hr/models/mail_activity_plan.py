# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class MailActivityPlan(models.Model):
    _inherit = 'mail.activity.plan'

    department_id = fields.Many2one('hr.department', check_company=True)

    def _validate_transition_from_dedicated(self, dedicated_res_model):
        super()._validate_transition_from_dedicated(dedicated_res_model)
        if dedicated_res_model == 'hr.employee':
            error = False
            template_ids = []
            for plan in self:
                if plan.department_id:
                    plan.department_id = False
                for template in plan.template_ids:
                    template_ids.append(template.id)

            if not error:
                for data in self.env['mail.activity.plan.template'].search_read(
                        [('id', 'in', template_ids)], ['responsible_type']):
                    if data['responsible_type'] in ('coach', 'manager', 'employee'):
                        error = f"responsible: {data['responsible_type']}"
                        break
            if error:
                raise UserError(_('Cannot generalize the plans because they are employee specific (field: %s).', error))
