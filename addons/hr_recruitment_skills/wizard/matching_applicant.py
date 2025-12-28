from odoo import fields, models


class MatchingApplicant(models.TransientModel):
    _name = "matching.applicant"
    _description = "Find applicants that match the job position based on their skills and educations"

    applicant_id = fields.Many2one("hr.applicant")
    job_id = fields.Many2one(related="applicant_id.job_id")
    matching_job_id = fields.Many2one("hr.job")
    matching_score = fields.Integer()
    matching_skills = fields.Many2many(
        comodel_name="hr.skill",
        relation="matching_applicant_matching_skills_rel",
        column1="matching_app",
        column2="matching_skill",
    )
    missing_skills = fields.Many2many(
        comodel_name="hr.skill",
        relation="matching_applicant_missing_skills_rel",
        column1="matching_app",
        column2="missing_skill",
    )

    def action_move_applicants_to_job(self):
        # TODO: Should we reset to the initial stage?
        self.applicant_id.write(
            {
                "job_id": self.matching_job_id.id,
                "stage_id": self.matching_job_id._get_first_stage().id,
            },
        )
        message = self.env._(
            " The following applicants were moved to the job position %(job_name)s: %(applicants_names)s",
            job_name=self.matching_job_id.name,
            applicants_names=", ".join({a.partner_name for a in self.applicant_id}),
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": message,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_copy_applicants_to_job(self):
        self.with_context(no_copy_in_partner_name=True).applicant_id.copy(
            {
                "job_id": self.matching_job_id.id,
                "stage_id": self.matching_job_id._get_first_stage().id,
            },
        )

        message = self.env._(
            "A new application for the following applicants was create for the job position %(job_name)s: %(applicants_names)s",
            job_name=self.matching_job_id.name,
            applicants_names=", ".join({a.partner_name for a in self.applicant_id}),
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": message,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
