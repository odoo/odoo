# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo.addons.website_event.controllers.community import EventCommunityController
from odoo.http import request, route


class WebsiteEventTrackQuizMeetController(EventCommunityController):

    @route()
    def community(self, event, page=1, lang=None, **kwargs):
        # website_event_track_quiz
        values = self._get_community_leaderboard_render_values(event, kwargs.get('search'), page)
        view = event.community_menu_ids.sudo().view_id
        page = view.key
        seo_object = request.website.get_template(page)

        # website_event_meet
        values.update(self._event_meeting_rooms_get_values(event, lang=lang) | {'seo_object': seo_object})
        return request.render('website_event.template_community', values)
