# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrRecruitmentPostJobWizard(models.TransientModel):
    _inherit = 'hr.recruitment.post.job.wizard'

    def _prepare_monster_data(self):
        self.ensure_one()
        data = super()._prepare_monster_data()
        if self.job_id.skill_ids:
            data['JobInformation']['JobSkills'] = {
                    'JobSkill': [{'Name': skill.name} for skill in self.job_id.skill_ids],
                }
        return data
