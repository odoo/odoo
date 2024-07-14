# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    social_post_ids = fields.One2many(compute="_compute_social_post_ids", groups="social.group_social_user")
    social_push_notification_ids = fields.One2many("social.post", "utm_campaign_id", compute="_compute_social_post_ids", string="Push Notifications", groups="social.group_social_user")
    social_push_notifications_count = fields.Integer(compute='_compute_social_push_notifications_count', string='Number Of Push Notifications', groups="social.group_social_user")

    def _compute_social_post_ids(self):
        """social_post_ids has to contain every posts that have at least one 'real' social media
        like twitter or facebook. Posts that are nothing but push notifications are filtered out of social_post_ids
        and affected to social_push_notification_ids.
        Posts that are linked to real social media and push notifications will be present in both fields"""

        push_notification_media_id = self.env.ref('social_push_notifications.social_media_push_notifications').id
        for campaign in self:
            campaign.social_post_ids = self.env['social.post'].search([('utm_campaign_id', 'in', campaign.ids)])
            campaign.social_push_notification_ids = campaign.social_post_ids.filtered(lambda post: push_notification_media_id in post.media_ids.ids)
            # Filter out the posts who are only push notifications
            campaign.social_post_ids = campaign.social_post_ids - campaign.social_push_notification_ids.filtered(lambda push_notif: len(push_notif.media_ids) == 1)

    def _compute_social_push_notifications_count(self):
        push_notifications_data = self.env['social.post']._read_group(
            [('utm_campaign_id', 'in', self.ids), ('media_ids.media_type', '=', 'push_notifications')],
            ['utm_campaign_id'], ['__count'])
        mapped_data = {utm_campaign.id: count for utm_campaign, count in push_notifications_data}
        for campaign in self:
            campaign.social_push_notifications_count = mapped_data.get(campaign.id, 0)

    def action_redirect_to_push_notifications(self):
            action = self.env["ir.actions.actions"]._for_xml_id("social.action_social_post")
            action['domain'] = [('utm_campaign_id', '=', self.id), ('media_ids.media_type', '=', 'push_notifications')]
            action['context'] = {
                "with_searchpanel": True,
                "searchpanel_default_state": "posted",
                "search_default_utm_campaign_id": self.id,
                "default_utm_campaign_id": self.id
            }
            return action

    def action_send_push_notification(self):
        push_media = self.env['social.media'].search([('media_type', '=', 'push_notifications')])
        action = self.env["ir.actions.actions"]._for_xml_id("social.action_social_post")
        action['views'] = [[False, 'form']]
        action['context'] = {
            'default_account_ids': push_media.account_ids.ids,
            'search_default_utm_campaign_id': self.id,
            'default_utm_campaign_id': self.id
        }
        return action

    def _get_social_posts_domain(self):
        domain = super(UtmCampaign, self)._get_social_posts_domain()
        return expression.AND([domain, [('media_ids.media_type', '!=', 'push_notifications')]])

    def _get_social_media_accounts_domain(self):
        domain = super(UtmCampaign, self)._get_social_media_accounts_domain()
        return expression.AND([domain, [('media_type', '!=', 'push_notifications')]])
