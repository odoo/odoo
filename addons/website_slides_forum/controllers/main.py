# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides


class WebsiteSlidesForum(WebsiteSlides):

    def _slide_channel_prepare_values(self, **kwargs):
        communication_type = kwargs.get('communication_type')
        channel = super(WebsiteSlidesForum, self)._slide_channel_prepare_values(**kwargs)
        if communication_type:
            if communication_type == 'forum':
                forum = request.env['forum.forum'].create({
                    'name': kwargs.get('name')
                })
                channel['forum_id'] = forum.id
        channel['allow_comment'] = communication_type == 'comment'
        return channel

    # Profile
    # ---------------------------------------------------

    def _prepare_user_profile_parameters(self, **post):
        post = super(WebsiteSlidesForum, self)._prepare_user_profile_parameters(**post)
        if post.get('channel_id'):
            channel = request.env['slide.channel'].browse(int(post.get('channel_id')))
            if channel.forum_id:
                post.update({
                    'forum_id': channel.forum_id.id,
                    'no_forum': False
                })
            else:
                post.update({'no_forum': True})
        return post
