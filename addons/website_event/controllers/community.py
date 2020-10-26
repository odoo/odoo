# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class EventCommunityController(http.Controller):

    @http.route('/event/<model("event.event"):event>/community', type="http", auth="public", website=True, sitemap=False)
    def community(self, event, lang=None, **kwargs):
        """ This skeleton route will be overriden in website_event_track_quiz, website_event_meet and website_event_meet_quiz. """
        return request.render('website.page_404')
