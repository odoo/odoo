# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class Job(models.Model):
    _inherit = "hr.job"
    _order = 'sequence, job_open_date'

    job_open_date = fields.Date('Job Start Recruitment Date', default=fields.Date.today())
    utm_campaign_id = fields.Many2one('utm.campaign', 'Campaign', ondelete='restrict')
    max_points = fields.Integer(compute='_compute_max_points')
    direct_clicks = fields.Integer(compute='_compute_clicks')
    facebook_clicks = fields.Integer(compute='_compute_clicks')
    twitter_clicks = fields.Integer(compute='_compute_clicks')
    linkedin_clicks = fields.Integer(compute='_compute_clicks')

    def _compute_clicks(self):
        if self.env.user.utm_source_id:
            grouped_data = self.env['link.tracker']._read_group([
                ('source_id', '=', self.env.user.utm_source_id.id),
                ('campaign_id', 'in', self.mapped('utm_campaign_id').ids),
                ('medium_id', '!=', False),
                ], ['campaign_id', 'medium_id'], ['count:sum'])
        else:
            grouped_data = {}
        medium_direct = self.env.ref('utm.utm_medium_direct', raise_if_not_found=False)
        medium_facebook = self.env.ref('utm.utm_medium_facebook', raise_if_not_found=False)
        medium_twitter = self.env.ref('utm.utm_medium_twitter', raise_if_not_found=False)
        medium_linkedin = self.env.ref('utm.utm_medium_linkedin', raise_if_not_found=False)
        mapped_data = {job.utm_campaign_id.id: {} for job in self}
        for campaign, medium, count in grouped_data:
            mapped_data[campaign.id][medium.id] = count
        for job in self:
            data = mapped_data[job.utm_campaign_id.id]
            job.direct_clicks = data.get(medium_direct.id, 0) if medium_direct else 0
            job.facebook_clicks = data.get(medium_facebook.id, 0) if medium_facebook else 0
            job.twitter_clicks = data.get(medium_twitter.id, 0) if medium_twitter else 0
            job.linkedin_clicks = data.get(medium_linkedin.id, 0) if medium_linkedin else 0

    def _compute_max_points(self):
        for job in self:
            stages = self.env['hr.recruitment.stage'].search([('use_in_referral', '=', True), '|', ('job_ids', '=', False), ('job_ids', '=', job.id)])
            job.max_points = sum(stages.mapped('points'))

    def set_recruit(self):
        self.write({'job_open_date': fields.Date.today()})
        return super(Job, self).set_recruit()

    def action_share_external(self):
        self.ensure_one()
        wizard = self.env['hr.referral.link.to.share'].create({'job_id': self.id})
        return {
            'name': _("Visit Webpage"),
            'type': 'ir.actions.act_url',
            'url': wizard.url,
            'target': 'new',
        }
