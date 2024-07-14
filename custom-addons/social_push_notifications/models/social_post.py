# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models, api


class SocialPostPushNotifications(models.Model):
    _inherit = 'social.post'

    use_visitor_timezone = fields.Boolean(compute='_compute_use_visitor_timezone', readonly=False, store=True)

    @api.depends('post_method')
    def _compute_use_visitor_timezone(self):
        for post in self:
            if post.post_method == 'now' or not post.use_visitor_timezone:
                post.use_visitor_timezone = False

    def _action_post(self):
        """ We also setup a CRON trigger at "now" to run the job as soon as possible to get the
        minimum amount of delay for the end user as push notifications are only sent when the CRON
        job runs (see social_push_notifications/social_live_post.py#_post). """

        super(SocialPostPushNotifications, self)._action_post()

        if 'push_notifications' in self.account_ids.mapped('media_type') and self.post_method == 'now':
            # trigger CRON job ASAP so that push notifications are sent
            cron = self.env.ref('social.ir_cron_post_scheduled')
            cron._trigger(at=fields.Datetime.now())

    @api.model
    def _cron_publish_scheduled(self):
        """ This method is overridden to gather all pending push live.posts ('ready' state) and post them.
        This is done in the cron job instead of instantly to avoid blocking the 'Post' action of the user
        indefinitely.

        The related social.post will remain 'pending' until all live.posts are processed. """

        super(SocialPostPushNotifications, self)._cron_publish_scheduled()

        ready_live_posts = self.env['social.live.post'].search([
            ('state', 'in', ['ready', 'posting'])
        ])
        push_notifications_live_posts = ready_live_posts._filter_by_media_types(['push_notifications'])
        push_notifications_live_posts.write({
            'state': 'posting'
        })
        push_notifications_live_posts._post_push_notifications()
