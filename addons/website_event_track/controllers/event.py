# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.addons.website.controllers.main import Website as controllers
import re

controllers = controllers()

class website_event(http.Controller):
    @website.route(['/event/<model("event.event"):event>/track/<model("event.track"):track>'], type='http', auth="public", multilang=True)
    def event_track_view(self, event, track, **post):
        # TODO: not implemented
        website.preload_records(event, on_error="website_event.404")
        website.preload_records(track)
        values = { 'track': track, 'event': track.event_id, 'main_object': track }
        return request.website.render("website_event_track.track_view", values)

    @website.route([
        '/event/<model("event.event"):event>/track/',
        '/event/<model("event.event"):event>/track/tag/<model("event.track.tag"):tag>'
        ], type='http', auth="public", multilang=True)
    def event_tracks(self, event, tag=None, **post):
        website.preload_records(event, on_error="website_event.404")
        website.preload_records(tag)
        searches = {}

        if tag:
            searches.update(tag=tag.id)
            track_obj = request.registry.get('event.track')
            track_ids = track_obj.search(request.cr, request.uid,
                [("id", "in", [track.id for track in event.track_ids]), ("tag_ids", "=", tag.id)], context=request.context)
            tracks = track_obj.browse(request.cr, request.uid, track_ids, context=request.context)
        else:
            tracks = event.track_ids

        def html2text(html):
            return re.sub(r'<[^>]+>', "", html)

        values = {
            'event': event,
            'main_object': event,
            'tracks': tracks,
            'tags': event.tracks_tag_ids,
            'searches': searches,
            'html2text': html2text
        }
        return request.website.render("website_event_track.tracks", values)

    @website.route(['/event/detail/<model("event.event"):event>'], type='http', auth="public", multilang=True)
    def event_detail(self, event, **post):
        website.preload_records(event, on_error="website_event.404")
        values = { 'event': event, 'main_object': event }
        return request.website.render("website_event_track.event_home", values)

    @website.route(['/event/<model("event.event"):event>/track_proposal/'], type='http', auth="public", multilang=True)
    def event_track_proposal(self, event, **post):
        website.preload_records(event, on_error="website_event.404")
        values = { 'event': event }
        return request.website.render("website_event_track.event_track_proposal", values)

    @website.route(['/event/<model("event.event"):event>/track_proposal/success/'], type='http', auth="public", multilang=True)
    def event_track_proposal_success(self, event, **post):
        website.preload_records(event, on_error="website_event.404")
        values = { 'event': event }
        return request.website.render("website_event_track.event_track_proposal_success", values)
