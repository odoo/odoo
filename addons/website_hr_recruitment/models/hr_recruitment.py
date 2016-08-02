# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urlparse import urljoin
from werkzeug import url_encode

from odoo import api, fields, models
from odoo.addons.website.models.website import slug
from odoo.tools.translate import html_translate


class RecruitmentSource(models.Model):
    _inherit = 'hr.recruitment.source'

    url = fields.Char(compute='_compute_url', string='Url Parameters')

    @api.one
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


class Applicant(models.Model):

    _inherit = 'hr.applicant'

    def website_form_input_filter(self, request, values):
        if 'partner_name' in values:
            values.setdefault('name', '%s\'s Application' % values['partner_name'])
        return values


class Job(models.Model):

    _name = 'hr.job'
    _inherit = ['hr.job', 'website.seo.metadata', 'website.published.mixin']

    website_description = fields.Html('Website description', translate=html_translate, sanitize=False)

    @api.multi
    def _website_url(self, field_name, arg):
        result = super(Job, self)._website_url(field_name, arg)
        for job in self:
            result[job.id] = "/jobs/detail/%s" % job.id
        return result

    @api.multi
    def set_open(self):
        self.write({'website_published': False})
        return super(Job, self).set_open()
