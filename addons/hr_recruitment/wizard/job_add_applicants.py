from odoo import Command, fields, models


class JobAddApplicants(models.TransientModel):
    _name = "job.add.applicants"
    _description = "Add applicants to a job"

    applicant_ids = fields.Many2many("hr.applicant", string="Applications", required=True)
    job_ids = fields.Many2many("hr.job", string="Job Positions", required=True)

    def _add_applicants_to_job(self):
        applicants = self.with_context(no_copy_in_partner_name=True).applicant_ids
        applicant_data = []
        for applicant in applicants:
            applicant_attachments = self.env['ir.attachment']
            for attachment in applicant.attachment_ids:
                applicant_attachments |= attachment.copy({
                    'res_id': applicant.id
                })
            applicant_data.append(applicant.copy_data({
                'attachment_ids': [Command.link(applicant_attachment.id)
                                   for applicant_attachment in applicant_attachments]
            })[0])

        new_applicants = self.env["hr.applicant"].create(
            [
                {
                    **applicant,
                    "job_id": job.id,
                    "talent_pool_ids": False,
                }
                for applicant in applicant_data
                for job in self.job_ids
            ]
        )
        return new_applicants

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
                names=", ".join({a.partner_name for a in new_applicants}),
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
