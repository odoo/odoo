# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class RecruitmentSource(models.Model):
    _inherit = 'hr.recruitment.source'

    url = fields.Char(related='link_tracker_id.short_url', string='Url Parameters')
    link_tracker_id = fields.Many2one('link.tracker', compute='_compute_link_tracker_id', store=True)
    click = fields.Integer(string='Clicks', related='link_tracker_id.count')

    @api.depends('campaign_id', 'source_id', 'job_id.website_url')
    def _compute_link_tracker_id(self):
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for source in self:
            link_tracker = self.env['link.tracker'].create({
                'url': str(web_base_url) + str(source.job_id.website_url),
                'title': source.job_id.name,
                'campaign_id': source.campaign_id.id,
                'source_id': source.source_id.id,
                'medium_id': self.env.ref('utm.utm_medium_website').id,
            })
            source.link_tracker_id = link_tracker

    def get_tracker_url(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': "%s+" % self.url
        }


class Applicant(models.Model):

    _inherit = 'hr.applicant'

    def website_form_input_filter(self, request, values):
        if 'partner_name' in values:
            values.setdefault('name', '%s\'s Application' % values['partner_name'])
        if values.get('job_id'):
            stage = self.env['hr.recruitment.stage'].sudo().search([
                ('fold', '=', False),
                '|', ('job_ids', '=', False), ('job_ids', '=', values['job_id']),
            ], order='sequence asc', limit=1)
            if stage:
                values['stage_id'] = stage.id
        return values


class Job(models.Model):

    _name = 'hr.job'
    _inherit = ['hr.job', 'website.seo.metadata', 'website.published.multi.mixin']

    def _get_default_website_description(self):
        default_description = self.env["ir.model.data"].xmlid_to_object("website_hr_recruitment.default_website_description")
        return (default_description._render() if default_description else "")

    website_description = fields.Html('Website description', translate=html_translate, sanitize_attributes=False, default=_get_default_website_description, prefetch=False, sanitize_form=False)

    def _compute_website_url(self):
        super(Job, self)._compute_website_url()
        for job in self:
            job.website_url = "/jobs/detail/%s" % job.id

    def set_open(self):
        self.write({'website_published': False})
        return super(Job, self).set_open()

    def get_backend_menu_id(self):
        return self.env.ref('hr_recruitment.menu_hr_recruitment_root').id

    def action_share_social_network(self):
        self.ensure_one()
        network = self.env.context['network']
        if network == 'facebook':
            utm_source = self.env.ref("utm.utm_source_facebook")
        elif network == 'twitter':
            utm_source = self.env.ref("utm.utm_source_twitter")
        elif network == 'linkedin':
            utm_source = self.env.ref("utm.utm_source_linkedin")

        sources = self.env['hr.recruitment.source'].search([
            ("source_id", "=", utm_source.id),
            ("job_id", "=", self.id)], order="create_date")

        if sources:
            source = sources[-1]
        else:
            source_vals = {
                'source_id': utm_source.id,
                'job_id': self.id,
            }
            source = self.env['hr.recruitment.source'].create(source_vals)

        if network == 'facebook':
            url = 'https://www.facebook.com/sharer/sharer.php?u=%s' % source.url
        elif network == 'twitter':
            url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing job offer for %s! Check it live: %s' % (self.name, source.url)
        elif network == 'linkedin':
            url = 'https://www.linkedin.com/sharing/share-offsite/?url=%s' % source.url

        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url
        }
