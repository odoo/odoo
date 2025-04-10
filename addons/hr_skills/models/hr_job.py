from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    job_skill_ids = fields.One2many(
        comodel_name="hr.job.skill",
        inverse_name="job_id",
        string="Skills",
        domain=[("skill_type_id.active", "=", True)],
    )
    current_job_skill_ids = fields.One2many(
        comodel_name="hr.job.skill",
        compute="_compute_current_job_skill_ids",
        readonly=False,
    )
    skill_ids = fields.Many2many(
        comodel_name="hr.skill",
        compute="_compute_skill_ids",
        store=True,
    )

    @api.depends("job_skill_ids")
    def _compute_current_job_skill_ids(self):
        current_job_skill_by_job = self.job_skill_ids._get_current_skills_by_job()
        for job in self:
            job.current_job_skill_ids = current_job_skill_by_job[job.id]

    @api.depends("job_skill_ids.skill_id")
    def _compute_skill_ids(self):
        for job in self:
            job.skill_ids = job.job_skill_ids.skill_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals_job_skill = vals.pop("current_job_skill_ids", []) + vals.get("job_skill_ids", [])
            vals["job_skill_ids"] = self.env["hr.job.skill"]._get_transformed_commands(vals_job_skill, self)
        return super().create(vals_list)

    def write(self, vals):
        if "current_job_skill_ids" in vals or "job_skill_ids" in vals:
            vals_job_skill = vals.pop("current_job_skill_ids", []) + vals.get("job_skill_ids", [])
            vals["job_skill_ids"] = self.env["hr.job.skill"]._get_transformed_commands(vals_job_skill, self)
        return super().write(vals)
