from ..models import monster_requests

from odoo import api, fields, models, _


class HrRecruitmentPostJobWizard(models.TransientModel):
    _inherit = 'hr.recruitment.post.job'

    post_to_monster = fields.Boolean()

    def action_post_job(self):
        for wizard in self:
            if wizard.post_to_monster:
                apply_method = wizard._get_apply_method()
                client = monster_requests.MonsterRequests(username=self.job_id.company_id.hr_recruitment_monster_username,
                                                          password=self.job_id.company_id.hr_recruitment_monster_password,
                                                          job_data=wizard.job_id._get_monster_data(),
                                                          test_environment=wizard.is_test)
                if apply_method.get('method') == 'email':
                    client.set_direct_apply(apply_method.get('value'))
                else:
                    client.set_redirect_apply(apply_method.get('value'))
                client.set_job_title(wizard.job_title)
                result = client.post_job()
                print(result)
                self.env['hr.job.post'].create({
                    'job_id': wizard.job_id.id,
                    'provider': "Monster",
                    'status': 'success'
                })
