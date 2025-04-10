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
        comodel_name="hr.applicant",
        required=True,
        index=True,
        ondelete="cascade",
    )

    def _linked_field_name(self):
        return "applicant_id"

    def _get_current_skills_by_applicant(self):
        applicant_skill_grouped = self.grouped(lambda a_s: (a_s.applicant_id, a_s.skill_id))
        result_dict = defaultdict(lambda: self.env["hr.applicant.skill"])
        for (applicant, skill), applicant_skills in applicant_skill_grouped.items():
            filtered_applicant_skills = applicant_skills.filtered(
                lambda a_s: not a_s.valid_to or a_s.valid_to >= fields.Date.today(),
            )
            if skill.skill_type_id.is_certification and not filtered_applicant_skills:
                most_recent_certification = max(applicant_skills, key=lambda a_s: a_s.valid_to)
                result_dict[applicant.id] += most_recent_certification
                continue
            result_dict[applicant.id] += filtered_applicant_skills
        return result_dict
