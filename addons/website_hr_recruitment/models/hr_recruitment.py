# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class RecruitmentSource(models.Model):
    _inherit = 'hr.recruitment.source'

    url = fields.Char(compute='_compute_url', string='Url Parameters')

    @api.depends('source_id', 'source_id.name', 'job_id', 'job_id.company_id')
    def _compute_url(self):
        for source in self:
            source.url = urls.url_join(source.job_id.get_base_url(), "%s?%s" % (
                source.job_id.website_url,
                urls.url_encode({
                    'utm_campaign': self.env.ref('hr_recruitment.utm_campaign_job').name,
                    'utm_medium': source.medium_id.name or self.env.ref('utm.utm_medium_website').name,
                    'utm_source': source.source_id.name
                })
            ))


class Applicant(models.Model):

    _inherit = 'hr.applicant'

    def website_form_input_filter(self, request, values):
        if 'partner_name' in values:
            applicant_job = self.env['hr.job'].sudo().search([('id', '=', values['job_id'])]).name if 'job_id' in values else False
            name = '%s - %s' % (values['partner_name'], applicant_job) if applicant_job else _("%s's Application", values['partner_name'])
            values.setdefault('name', name)
        if values.get('job_id'):
            job = self.env['hr.job'].browse(values.get('job_id'))
            if not job.sudo().website_published:
                raise UserError(_("You cannot apply for this job."))
            stage = self.env['hr.recruitment.stage'].sudo().search([
                ('fold', '=', False),
                '|', ('job_ids', '=', False), ('job_ids', '=', values['job_id']),
            ], order='sequence asc', limit=1)
            if stage:
                values['stage_id'] = stage.id
        return values
