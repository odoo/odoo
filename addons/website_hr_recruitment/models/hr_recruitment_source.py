# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urlparse import urljoin
from werkzeug import url_encode

from odoo import api, fields, models

class HrRecruitmentSource(models.Model):
    _inherit = 'hr.recruitment.source'

    url = fields.Char(compute='_compute_url', string='Url Parameters')

    @api.depends('source_id', 'source_id.name', 'job_id')
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
