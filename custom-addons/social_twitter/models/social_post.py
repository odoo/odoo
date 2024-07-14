# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.osv import expression


class SocialPostTwitter(models.Model):
    _inherit = 'social.post'

    @api.depends('live_post_ids.twitter_tweet_id')
    def _compute_stream_posts_count(self):
        super()._compute_stream_posts_count()

    @api.depends('state')
    def _compute_twitter_post_limit_message(self):
        self.twitter_post_limit_message = False
        self.is_twitter_post_limit_exceed = False
        super(SocialPostTwitter, self - self.filtered(lambda post: post.state in ['posting', 'posted']))._compute_twitter_post_limit_message()

    def _get_stream_post_domain(self):
        domain = super()._get_stream_post_domain()
        twitter_tweet_ids = [twitter_tweet_id for twitter_tweet_id in self.live_post_ids.mapped('twitter_tweet_id') if twitter_tweet_id]
        if twitter_tweet_ids:
            return expression.OR([domain, [('twitter_tweet_id', 'in', twitter_tweet_ids)]])
        return domain

    @api.model
    def _prepare_post_content(self, message, media_type, **kw):
        message = super()._prepare_post_content(message, media_type, **kw)
        if message and media_type == 'twitter':
            message = self.env["social.live.post"]._remove_mentions(message)
        return message
