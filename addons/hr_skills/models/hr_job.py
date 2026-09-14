from odoo import fields, models


class HrJob(models.Model):
    _inherit = ["mixin.hr.individual.skill.owner", "hr.job"]

    job_skill_ids = fields.One2many(
        comodel_name="hr.job.skill",
        inverse_name="job_id",
        string="Skills",
        domain=[("skill_type_id.active", "=", True)],
    )
    current_job_skill_ids = fields.One2many(
        comodel_name="hr.job.skill",
        compute="_compute_current_individual_skill_ids",
        search="_search_current_individual_skill_ids",
        readonly=False,
    )
    skill_ids = fields.Many2many(
        comodel_name="hr.skill",
        compute="_compute_skill_ids",
        search="_search_skill_ids",
    )

    def _individual_skill_field_name(self):
        return "job_skill_ids"

    def _current_individual_skill_field_name(self):
        return "current_job_skill_ids"
