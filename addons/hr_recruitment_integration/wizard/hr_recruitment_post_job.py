from odoo import api, fields, models, _


class HrRecruitmentPostJobWizard(models.TransientModel):
    _name = 'hr.recruitment.post.job'
    _description = 'Post Job'

    job_id = fields.Many2one('hr.job', string="Job")
    job_title = fields.Char(string="Job Title")
    job_apply_mail = fields.Char(string="Email")
    is_test = fields.Boolean(string="Is Test")

    def _get_apply_method(self):
        """
        Method to get the way applicants will apply on a given job board, defaults to the alias mail of the job if
        website_hr_recruitment is not installed.
        """
        return {
            'method': 'email',
            'value': self.job_apply_mail
        }

    def action_post_job(self):
        raise NotImplementedError
