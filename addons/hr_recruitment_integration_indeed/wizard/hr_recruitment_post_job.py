from odoo import api, fields, models, _


class HrRecruitmentPostJobWizard(models.TransientModel):
    _inherit = 'hr.recruitment.post.job'

    post_to_indeed = fields.Boolean()

    def action_post_job(self):
        for wizard in self:
            if wizard.post_to_indeed:
                apply_method = wizard._get_apply_method()

