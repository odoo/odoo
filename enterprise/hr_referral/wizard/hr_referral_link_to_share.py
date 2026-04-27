# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        ('twitter', 'X'),
        ('linkedin', 'Linkedin')], default='direct')
    url = fields.Char(readonly=True, compute='_compute_url', compute_sudo=True)

    @api.depends('channel')
    def _compute_url(self):
        channel_to_medium = {
            'direct': 'utm.utm_medium_direct',
            'facebook': 'utm.utm_medium_facebook',
            'twitter': 'utm.utm_medium_twitter',
            'linkedin': 'utm.utm_medium_linkedin',
        }

        if not self.env.user.utm_source_id:
            self.env.user.utm_source_id = self.env['utm.source'].create({
                'name': self.env['utm.source']._generate_name(self.env.user, self.env.user.name),
            }).id

        jobs_without_campaign = [
            wizard.job_id for wizard in self
            if wizard.job_id and not wizard.job_id.utm_campaign_id
        ]
        if jobs_without_campaign:
            utm_campaign = []
            for job in jobs_without_campaign:
                utm_campaign.append({'name': _('Referral: %(name)s', name=job.name)})
            utm_campaign_ids = self.env['utm.campaign'].create(utm_campaign).ids
            for utm_campaign_id, job in zip(utm_campaign_ids, jobs_without_campaign):
                job.utm_campaign_id = utm_campaign_id

        link_trackers_values = []
        for wizard in self:
            url = url_join(self.get_base_url(), '/jobs') if not wizard.job_id else wizard.job_id.full_url
            link_trackers_values.append({
                'title': _('Referral: %(url)s', url=url),
                'url': url,
                'campaign_id': wizard.job_id.utm_campaign_id.id,
                'source_id': wizard.env.user.utm_source_id.id,
            })

            medium_reference = channel_to_medium.get(wizard.channel)
            medium = self.env.ref(medium_reference, raise_if_not_found=False) if medium_reference else False
            if medium:
                link_trackers_values[-1]['medium_id'] = medium.id

        link_trackers = self.env['link.tracker'].search_or_create(link_trackers_values)

        for wizard, link_tracker in zip(self, link_trackers):
            if wizard.channel == 'direct':
                wizard.url = link_tracker.short_url
            elif wizard.channel == 'facebook':
                wizard.url = 'https://www.facebook.com/sharer/sharer.php?u=%s' % link_tracker.short_url
            elif wizard.channel == 'twitter':
                wizard.url = 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=Amazing' + \
                    ' job offer for %s! Check it live: %s' % (self.job_id.name, link_tracker.short_url)
            elif wizard.channel == 'linkedin':
                wizard.url = 'https://www.linkedin.com/sharing/share-offsite?url=%s' % link_tracker.short_url
