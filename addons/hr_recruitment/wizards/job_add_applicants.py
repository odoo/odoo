from odoo import fields, models


class JobAddApplicants(models.TransientModel):
    _name = "job.add.applicants"
    _description = "Add applicants to a job"

    applicant_ids = fields.Many2many(
        comodel_name="hr.applicant",
        string="Applications",
        required=True,
    )
    job_ids = fields.Many2many(
        comodel_name="hr.job",
        string="Job Positions",
        required=True,
    )

    def _add_applicants_to_job(self):
        applicant_data = self.with_context(
            no_copy_in_partner_name=True
        ).applicant_ids.copy_data()
        first_stage_by_job = self.env["hr.recruitment.stage"]._get_first_stage_by_job(
            self.job_ids
        )
        new_applicants_vals = [
            {
                **applicant,
                "job_id": job.id,
                "talent_pool_ids": False,
                "stage_id": first_stage_by_job[job].id,
            }
            for applicant in applicant_data
            for job in self.job_ids
        ]
        return self.env["hr.applicant"].create(new_applicants_vals)

    def action_add_applicants_to_job(self):
        new_applicants = self._add_applicants_to_job()

        if len(new_applicants) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "hr.applicant",
                "view_mode": "form",
                "target": "current",
                "res_id": new_applicants.id,
            }
        else:
            message = self.env._(
                "Created %(amount)s new applications for: %(names)s",
                amount=len(new_applicants),
                names=", ".join(
                    dict.fromkeys(
                        a.partner_name for a in new_applicants if a.partner_name
                    )
                ),
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
