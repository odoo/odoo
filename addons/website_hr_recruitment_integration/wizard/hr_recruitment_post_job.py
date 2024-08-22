from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug
from werkzeug.urls import url_encode, url_join


class HrRecruitmentPostJobWizard(models.TransientModel):
    _inherit = 'hr.recruitment.post.job'

    apply_method = fields.Selection([
        ('email', 'Direct Apply'),
        ('redirect', 'Redirect to Website'),
    ], default='redirect', string="Apply Method")

    def _get_apply_method(self):
        if self.apply_method == 'redirect' and self.job_id.website_published:
            return {
                'method': 'redirect',
                'value': url_join(self.job_id.get_base_url(), '/jobs/apply/%s' % self.job_id.id)
            }
        else:
            return super()._get_apply_method()
