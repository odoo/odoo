from werkzeug.urls import url_join

from odoo import fields, models


class HrRecruitmentPostJobWizard(models.TransientModel):
    _inherit = 'hr.recruitment.post.job'

    apply_method = fields.Selection(
        selection_add=[
            ('redirect', 'Redirect to Website'),
        ], default='redirect')

    def _get_apply_method(self):
        if self.apply_method == 'redirect' and self.job_id.website_published:
            return {
                'method': 'redirect',
                'value': url_join(self.job_id.get_base_url(), '/jobs/apply/%s' % self.job_id.id)
            }
        else:
            return super()._get_apply_method()
