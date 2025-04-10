# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import fields, models


class HrJobSkill(models.Model):
    _name = "hr.job.skill"
    _inherit = "hr.individual.skill.mixin"
    _description = "Skills for job positions"
    _order = "skill_type_id, skill_level_id desc"
    _rec_name = "skill_id"

    job_id = fields.Many2one(
        comodel_name="hr.job",
        required=True,
        index=True,
        ondelete="cascade",
    )

    def _linked_field_name(self):
        return "job_id"

    def get_current_skills_by_job(self):
        job_skill_grouped = self.grouped(lambda j_s: (j_s.job_id, j_s.skill_id))
        result_dict = defaultdict(lambda: self.env["hr.job.skill"])
        for (job, skill), job_skill in job_skill_grouped.items():
            filtered_job_skill = job_skill.filtered(
                lambda j_s: not j_s.valid_to or j_s.valid_to >= fields.Date.today(),
            )
            if skill.skill_type_id.is_certification and not filtered_job_skill:
                expired_skills = job_skill - filtered_job_skill
                expired_skills_group_by_valid_to = expired_skills.grouped("valid_to")
                max_valid_to = max(expired_skills.mapped("valid_to"))
                result_dict[job.id] += expired_skills_group_by_valid_to[max_valid_to]
                continue
            result_dict[job.id] += filtered_job_skill
        return result_dict
