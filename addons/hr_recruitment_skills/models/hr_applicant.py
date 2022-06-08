# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    applicant_skill_ids = fields.One2many('hr.applicant.skill', 'applicant_id', string="Skills")

    def create_employee_from_applicant(self):
        self.ensure_one()
        action = super().create_employee_from_applicant()
        action['context']['default_employee_skill_ids'] = [(0, 0, {
            'skill_id': applicant_skill.skill_id.id,
            'skill_level_id': applicant_skill.skill_level_id.id,
            'skill_type_id': applicant_skill.skill_type_id.id,
        }) for applicant_skill in self.applicant_skill_ids]
        return action
