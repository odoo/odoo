# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import api, fields, models
from odoo.tools import urls


class HrRecruitmentSource(models.Model):
    _inherit = 'hr.recruitment.source'

    url = fields.Char(compute='_compute_url', string='Tracker URL')

    @api.depends('source_id', 'source_id.name', 'job_id', 'job_id.company_id')
    def _compute_url(self):
        for source in self:
            source.url = urls.urljoin(source.job_id.get_base_url(), "%s?%s" % (
                source.job_id.website_url,
                url_encode({
                    'utm_campaign': self.env.ref('hr_recruitment.utm_campaign_job').name,
                    'utm_medium': source.medium_id.name or self.env['utm.medium']._fetch_or_create_utm_medium('website').name,
                    'utm_source': source.source_id.name or None
                }),
            ))
