# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo.addons.http_routing.models.ir_http import slug
from odoo import http
from odoo.http import request
from odoo.addons.website_profile.controllers.main import WebsiteProfile


class WebsiteSlidesForum(WebsiteProfile):
    # Profile
    # ---------------------------------------------------
    @http.route(['/slides/<model("slide.channel"):channel>/user/<int:user_id>'], type='http', auth="public", website=True)
    def open_slide_user(self, channel, user_id=0, **post):
        user = request.env['res.users'].sudo().browse(user_id)
        current_user = request.env.user.sudo()

        # Users with high karma can see users with karma <= 0 for
        # moderation purposes, IFF they have posted something (see below)
        if (not user or (user.karma < 1 and current_user.karma < channel.karma_unlink_all)):
            return werkzeug.utils.redirect("/slides/%s" % slug(channel))
        values = self._prepare_user_values(channel=channel, forum=channel.forum_id, **post)

        values.update(self._prepare_open_slide_user(user))
        values.update(self._prepare_open_forum_user(user, current_user, channel.forum_id, values, **post))
        if not values['is_profile_page']:
            return request.render("website_slides_forum.private_profile_slide_forum", values, status=404)
        return request.render("website_slides_forum.user_detail_full", values)

    @http.route(['/slides/user/<int:user_id>'], type='http', auth="public", website=True)
    def open_cross_slide_user(self, user_id=0, **post):
        user = request.env['res.users'].sudo().browse([user_id])
        current_user = request.env.user.sudo()

        if post.get('channel'):
            channels = post.get('channel')
        elif post.get('channel_id'):
            channels = request.env['slide.channel'].browse(int(post.get('channel_id')))
        else:
            channels = request.env['slide.channel'].search([])

        if len(channels) == 1:
            forums = channels[0].forum_id
        else:
            forums = channels.mapped('forum_id')

        values = {
            'user': request.env.user,
            'is_public_user': request.env.user.id == request.website.user_id.id,
            'notifications': self._get_notifications(),
            'header': post.get('header', dict()),
            'searches': post.get('searches', dict()),
            'validation_email_sent': request.session.get('validation_email_sent', False),
            'validation_email_done': request.session.get('validation_email_done', False),
            'channel': channels[0] if len(channels) == 1 else True,
            'forum': forums[0] if len(forums) == 1 else False if len(forums) == 0 else True,
        }

        values.update(self._prepare_open_forum_user(user, current_user, forums, values, **post))
        if forums and not values['is_profile_page']:
            return request.render("website_slides_forum.private_profile_slide_forum", values, status=404)

        values.update(self._prepare_open_slide_user(user))
        return request.render("website_slides_forum.user_detail_cross_full", values)

    @http.route(['/profile/user/<int:user_id>'], type='http', auth="public", website=True)
    def open_profile_user(self, user_id=0, **post):
        user = request.env['res.users'].sudo().browse([user_id])
        current_user = request.env.user.sudo()

        channels = request.env['slide.channel'].search([])
        forums = request.env['forum.forum'].search([])

        values = {
            'user': request.env.user,
            'is_public_user': request.env.user.id == request.website.user_id.id,
            'notifications': self._get_notifications(),
            'header': post.get('header', dict()),
            'searches': post.get('searches', dict()),
            'validation_email_sent': request.session.get('validation_email_sent', False),
            'validation_email_done': request.session.get('validation_email_done', False),
            'channel': channels[0] if len(channels) == 1 else True,
            'forum': forums[0] if len(forums) == 1 else True,
        }

        values.update(self._prepare_open_forum_user(user, current_user, forums, values, **post))
        if forums and not values['is_profile_page']:
            return request.render("website_slides_forum.private_profile", values, status=404)

        values.update(self._prepare_open_slide_user(user))
        return request.render("website_profile.user_detail_main", values)
