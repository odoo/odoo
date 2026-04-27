# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    social_post_ids = fields.One2many('social.post', 'utm_campaign_id', string="All related social media posts", groups="social.group_social_user")
    social_posts_count = fields.Integer(compute="_compute_social_posts_count", string='Social Media Posts', groups="social.group_social_user")
    social_engagement = fields.Integer(compute="_compute_social_engagement", string='Number of interactions (likes, shares, comments ...) with the social posts', groups="social.group_social_user")

    def _compute_social_engagement(self):
        campaigns_engagement = {campaign.id: 0 for campaign in self}

        posts_data = self.env['social.post'].search_read(
            [('utm_campaign_id', 'in', self.ids)],
            ['utm_campaign_id', 'engagement']
        )

        for datum in posts_data:
            campaign_id = datum['utm_campaign_id'][0]
            campaigns_engagement[campaign_id] += datum['engagement']

        for campaign in self:
            campaign.social_engagement = campaigns_engagement[campaign.id]

    def _compute_social_posts_count(self):
        domain = expression.AND([self._get_social_posts_domain(), [('utm_campaign_id', 'in', self.ids)]])
        post_data = self.env['social.post']._read_group(
            domain,
            ['utm_campaign_id'], ['__count']
        )

        mapped_data = {utm_campaign.id: count for utm_campaign, count in post_data}

        for campaign in self:
            campaign.social_posts_count = mapped_data.get(campaign.id, 0)

    def action_create_new_post(self):
        action = self.env["ir.actions.actions"]._for_xml_id("social.action_social_post")
        action['views'] = [[False, 'form']]
        action['context'] = {
            'default_utm_campaign_id': self.id,
            'default_account_ids': self.env['social.account'].search(self._get_social_media_accounts_domain()).ids
        }
        return action

    def action_redirect_to_social_media_posts(self):
        action = self.env["ir.actions.actions"]._for_xml_id("social.action_social_post")
        action['domain'] = self._get_social_posts_domain()
        action['context'] = {
            "searchpanel_default_state": "posted",
            "search_default_utm_campaign_id": self.id,
            "default_utm_campaign_id": self.id
        }
        return action

    def _get_social_posts_domain(self):
        """This method will need to be overriden in social_push_notifications to filter out posts who only are push notifications"""
        return []

    def _get_social_media_accounts_domain(self):
        """This method will need to be overriden in social_push_notifications to filter out push_notifications medium"""
        return []
