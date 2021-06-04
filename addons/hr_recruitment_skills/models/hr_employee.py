# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        appl_id = self.env.context.get('default_applicant_id')
        application_id = self.env['hr.applicant'].browse(appl_id)
        if 'employee_skill_ids' in fields_list and application_id:
            res['employee_skill_ids'] = []
            breakpoint()
            for skill_id in application_id.skill_ids:
                skill_level = skill_id.skill_type_id.skill_level_ids.sorted('level_progress')
                res['employee_skill_ids'].append((0, 0, {
                    'skill_id': skill_id.id,
                    'skill_level_id': skill_level[0],
                    'skill_type_id': skill_id.skill_type_id.id,
                }))
        return res
