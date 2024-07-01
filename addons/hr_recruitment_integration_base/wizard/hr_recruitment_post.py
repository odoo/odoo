from odoo import fields, models, _


class HrRecruitmentPostJobWizard(models.TransientModel):
    _name = 'hr.recruitment.post.job'
    _description = 'Post Job'

    job_id = fields.Many2one('hr.job', string="Job")
    job_title = fields.Char(string="Job Title")
    job_apply_mail = fields.Char(string="Email")
    is_test = fields.Boolean(string="Is Test")

    def _get_apply_method(self):
        return {
            'method': 'email',
            'value': self.job_apply_mail
        }

    def action_post_job(self):
        raise NotImplementedError
