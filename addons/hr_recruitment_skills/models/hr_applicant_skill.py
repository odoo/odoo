# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import fields, models


class HrApplicantSkill(models.Model):
    _name = 'hr.applicant.skill'
    _inherit = "hr.individual.skill.mixin"
    _description = "Skill level for an applicant"
    _rec_name = 'skill_id'
    _order = "skill_type_id, skill_level_id desc"

    applicant_id = fields.Many2one(
        comodel_name='hr.applicant',
        required=True,
        index=True,
        ondelete="cascade",
    )

    def _linked_field_name(self):
        return "applicant_id"

    def get_current_skills_by_applicant(self):
        applicant_skill_grouped = self.grouped(lambda a_s: (a_s.applicant_id, a_s.skill_id))
        result_dict = defaultdict(lambda: self.env["hr.applicant.skill"])
        for (applicant, skill), applicant_skill in applicant_skill_grouped.items():
            filtered_applicant_skill = applicant_skill.filtered(
                lambda a_s: not a_s.valid_to or a_s.valid_to >= fields.Date.today(),
            )
            if skill.skill_type_id.is_certification and not filtered_applicant_skill:
                expired_skills = applicant_skill - filtered_applicant_skill
                expired_skills_group_by_valid_to = expired_skills.grouped("valid_to")
                max_valid_to = max(expired_skills.mapped("valid_to"))
                result_dict[applicant.id] += expired_skills_group_by_valid_to[max_valid_to]
                continue
            result_dict[applicant.id] += filtered_applicant_skill
        return result_dict
