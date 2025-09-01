# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def _can_edit_certification_validity_period(self):
        return False
