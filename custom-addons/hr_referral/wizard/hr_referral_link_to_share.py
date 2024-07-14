# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from werkzeug.urls import url_join

from odoo import api, fields, models, _


class HrReferralLinkToShare(models.TransientModel):
    _name = 'hr.referral.link.to.share'
    _description = 'Referral Link To Share'

    job_id = fields.Many2one(
        'hr.job',
        default=lambda self: self.env.context.get('active_id', None),
    )
    channel = fields.Selection([
        ('direct', 'Link'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('linkedin', 'Linkedin')], default='direct')
    url = fields.Char(readonly=True, compute='_compute_url', compute_sudo=True)

    @api.depends('channel')
    def _compute_url(self):
        self.ensure_one()

        if not self.env.user.utm_source_id:
            self.env.user.utm_source_id = self.env['utm.source'].create({
                'name': self.env['utm.source']._generate_name(self, self.env.user.name),
            }).id

        if self.job_id and not self.job_id.utm_campaign_id:
            self.job_id.utm_campaign_id = self.env['utm.campaign'].create({'name': self.job_id.name}).id

        job_url = url_join(self.get_base_url(), (self.job_id.website_url or '/jobs'))
        link_tracker_values = {
            'title': _('Referral: %(job_url)s', job_url=job_url),
            'url': job_url,
            'campaign_id': self.job_id.utm_campaign_id.id,
            'source_id': self.env.user.utm_source_id.id,
        }

        channel_to_medium = {
            'direct': 'utm.utm_medium_direct',
            'facebook': 'utm.utm_medium_facebook',
            'twitter': 'utm.utm_medium_twitter',
            'linkedin': 'utm.utm_medium_linkedin',
        }
        medium_reference = channel_to_medium.get(self.channel)
        medium = self.env.ref(medium_reference, raise_if_not_found=False) if medium_reference else False
        if medium:
            link_tracker_values['medium_id'] = medium.id

        link_tracker = self.env['link.tracker'].search_or_create(link_tracker_values)
        if self.channel == 'direct':
            self.url = link_tracker.short_url
        elif self.channel == 'facebook':
            self.url = 'https://www.facebook.com/sharer/sharer.php?u=%s' % link_tracker.short_url
        elif self.channel == 'twitter':
            self.url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing job offer for %s! Check it live: %s' % (self.job_id.name, link_tracker.short_url)
        elif self.channel == 'linkedin':
            self.url = 'https://www.linkedin.com/sharing/share-offsite?url=%s' % link_tracker.short_url
