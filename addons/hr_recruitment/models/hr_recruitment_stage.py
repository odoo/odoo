from odoo import _, api, fields, models


class HrRecruitmentStage(models.Model):
    _name = "hr.recruitment.stage"
    _description = "Recruitment Stages"
    _order = "sequence"

    name = fields.Char(
        string="Stage Name",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    job_ids = fields.Many2many(
        comodel_name="hr.job",
        string="Job Specific",
        help="Specific jobs that use this stage. Other jobs will not use this stage.",
    )
    requirements = fields.Text()
    template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        help="If set, a message is posted on the applicant using the template when the applicant is set to the stage.",
    )
    fold = fields.Boolean(
        string="Folded in Kanban",
        help="This stage is folded in the kanban view when there are no records in that stage to display.",
    )
    hired_stage = fields.Boolean(
        help="If checked, this stage is used to determine the hire date of an applicant"
    )
    rotting_threshold_days = fields.Integer(
        string="Days to rot",
        default=0,
        help="Day count before applicants in this stage become stale. \
        Set to 0 to disable.  Changing this parameter will not affect the rotting status/date of resources last updated before this change.",
    )
    legend_blocked = fields.Char(
        string="Red Kanban Label",
        translate=True,
        default=lambda self: _("Blocked"),
        required=True,
    )
    legend_waiting = fields.Char(
        string="Orange Kanban Label",
        translate=True,
        default=lambda self: _("Waiting"),
        required=True,
    )
    legend_done = fields.Char(
        string="Green Kanban Label",
        translate=True,
        default=lambda self: _("Ready for Next Stage"),
        required=True,
    )
    legend_normal = fields.Char(
        string="Grey Kanban Label",
        translate=True,
        default=lambda self: _("In Progress"),
        required=True,
    )
    is_warning_visible = fields.Boolean(compute="_compute_is_warning_visible")

    @api.model
    def default_get(self, fields):
        if self.env.context.get("default_job_id") and not self.env.context.get(
            "hr_recruitment_stage_mono"
        ):
            context = dict(self.env.context)
            context.pop("default_job_id")
            self = self.with_context(context)
        return super().default_get(fields)

    @api.model
    def _get_first_stage_by_job(self, jobs):
        """The stage a new application lands in, per job.

        A job-specific stage wins over a generic one at the same sequence.
        """
        none = self.browse()
        stages_by_job = dict(
            self._read_group(
                [("job_ids", "in", jobs.ids + [False]), ("fold", "=", False)],
                ["job_ids"],
                ["id:recordset"],
            )
        )
        generic_stages = stages_by_job.get(self.env["hr.job"], none)
        first_stage_by_job = {}
        for job in jobs:
            job_stages = stages_by_job.get(job, none)
            candidates = job_stages | generic_stages
            if not candidates:
                first_stage_by_job[job] = none
                continue
            # By id, not by `stage not in job_stages`: recordset membership is a
            # scan, and this runs inside the comparison key.
            job_stage_ids = set(job_stages._ids)
            first_stage_by_job[job] = min(
                candidates,
                key=lambda stage: (
                    stage.sequence,
                    stage.id not in job_stage_ids,
                    stage.id,
                ),
            )
        return first_stage_by_job

    @api.depends("hired_stage")
    def _compute_is_warning_visible(self):
        applicant_data = self.env["hr.applicant"]._read_group(
            [("stage_id", "in", self.ids)], ["stage_id"], ["__count"]
        )
        applicants = {stage.id: count for stage, count in applicant_data}
        for stage in self:
            if (
                stage._origin.hired_stage
                and not stage.hired_stage
                and applicants.get(stage._origin.id)
            ):
                stage.is_warning_visible = True
            else:
                stage.is_warning_visible = False
