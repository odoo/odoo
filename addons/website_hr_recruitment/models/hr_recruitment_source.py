from urlparse import urljoin
from werkzeug import url_encode

from openerp import models, fields, api
from openerp.addons.website.models.website import slug

class HrRecruitmentSource(models.Model):
    _inherit = 'hr.recruitment.source'

    @api.depends('source_id', 'source_id.name', 'job_id')
    @api.one
    def _compute_url(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for source in self:
            source.url = urljoin(base_url, "%s?%s" % (source.job_id.website_url,
                url_encode({
                    'utm_campaign': self.env.ref('hr_recruitment.utm_campaign_job').name,
                    'utm_medium': self.env.ref('utm.utm_medium_website').name,
                    'utm_source': source.source_id.name
                })
            ))

    url = fields.Char(compute='_compute_url', string='Url Parameters')