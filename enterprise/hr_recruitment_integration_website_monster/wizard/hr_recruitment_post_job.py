# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrRecruitmentPostJobWizard(models.TransientModel):
    _inherit = 'hr.recruitment.post.job.wizard'

    def _prepare_monster_data(self):
        self.ensure_one()
        data = super()._prepare_monster_data()
        data['JobInformation']['Contact']['WebSite'] = self.get_base_url()
        if self.apply_method == 'redirect':
            data['JobInformation']['CustomApplyOnlineURL'] = self.job_id.full_url
        return data
