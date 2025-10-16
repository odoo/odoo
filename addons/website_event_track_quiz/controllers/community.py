# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import http
from odoo.addons.website_event.controllers.community import EventCommunityController
from odoo.http import request


class WebsiteEventTrackQuizCommunityController(EventCommunityController):

    _visitors_per_page = 30
    _pager_max_pages = 5

    @http.route(['/event/<model("event.event"):event>/community/leaderboard/results',
                 '/event/<model("event.event"):event>/community/leaderboard/results/page/<int:page>'],
                type='http', auth="public", website=True, sitemap=False)
    def leaderboard(self, event, page=1, lang=None, **kwargs):
        values = self._get_community_leaderboard_render_values(event, kwargs.get('search'), page)
        return request.render('website_event_track_quiz.event_leaderboard', values)

    @http.route('/event/<model("event.event"):event>/community/leaderboard',
                type='http', auth="public", website=True, sitemap=False)
    def community_leaderboard(self, event, **kwargs):
        values = self._get_community_leaderboard_render_values(event, None, None)
        return request.render('website_event_track_quiz.event_leaderboard', values)

    @http.route()
    def community(self, event, **kwargs):
        values = self._get_community_leaderboard_render_values(event, None, None)
        return request.render('website_event_track_quiz.event_leaderboard', values | {'seo_object': event.community_menu_ids})

    def _get_community_leaderboard_render_values(self, event, search_term, page):
        values = self._get_leaderboard(event, search_term)
        values.update({'event': event, 'search': search_term})

        user_count = len(values['visitors'])
        if user_count:
            page_count = math.ceil(user_count / self._visitors_per_page)
            url = '/event/%s/community/leaderboard/results' % (request.env['ir.http']._slug(event))
            if values.get('current_visitor_position') and not page:
                values['scroll_to_position'] = True
                page = math.ceil(values['current_visitor_position'] / self._visitors_per_page)
            elif not page:
                page = 1
            pager = request.website.pager(url=url, total=user_count, page=page, step=self._visitors_per_page,
                                          scope=page_count if page_count < self._pager_max_pages else self._pager_max_pages,
                                          url_args={'search': search_term})
            values['visitors'] = values['visitors'][(page - 1) * self._visitors_per_page: (page) * self._visitors_per_page]
        else:
            pager = {'page_count': 0}
        values.update({'pager': pager})
        return values

    def _get_leaderboard(self, event, searched_name=None):
        current_visitor = request.env['website.visitor']._get_visitor_from_request()
        track_visitor_data = request.env['event.track.visitor'].sudo()._read_group(
            [('track_id', 'in', event.track_ids.ids),
             ('visitor_id', '!=', False),
             ('quiz_points', '>', 0)],
            ['visitor_id'],
            ['quiz_points:sum'], order='quiz_points:sum DESC, visitor_id ASC')
        data_map = {visitor.id: points for visitor, points in track_visitor_data}
        leaderboard = []
        position = 1
        current_visitor_position = False
        visitors_by_id = {
            visitor.id: visitor
            for visitor in request.env['website.visitor'].sudo().browse(data_map.keys())
        }
        for visitor_id, points in data_map.items():
            visitor = visitors_by_id.get(visitor_id)
            if not visitor:
                continue
            if (searched_name and searched_name.lower() in visitor.display_name.lower()) or not searched_name:
                leaderboard.append({'visitor': visitor, 'points': points, 'position': position})
                if current_visitor and current_visitor == visitor:
                    current_visitor_position = position
            position = position + 1

        return {
            'top3_visitors': leaderboard[:3],
            'visitors': leaderboard,
            'current_visitor_position': current_visitor_position,
            'current_visitor': current_visitor,
            'searched_name': searched_name
        }
