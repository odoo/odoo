from odoo import fields, models


class HrApplicantSkill(models.Model):
    _name = "hr.applicant.skill"
    _inherit = "mixin.hr.individual.skill"
    _description = "Skill level for an applicant"
    _order = "skill_type_id, skill_level_id desc"

    applicant_id = fields.Many2one(
        comodel_name="hr.applicant",
        index=True,
        required=True,
        ondelete="cascade",
    )

    def _linked_field_name(self):
        return "applicant_id"
