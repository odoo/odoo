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
from openerp.tools.translate import _
from openerp.addons import website_sale
from openerp.addons.website.models import website
from openerp.addons.website.controllers.main import Website as controllers

controllers = controllers()


from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import tools
import urllib

class website_event(http.Controller):
    @website.route(['/event/track_view/<model("event.track"):track>'], type='http', auth="public", multilang=True)
    def event_track_view(self, track, **post):
        # TODO: not implemented
        values = { 'track': track, 'event': track.event_id}
        return request.website.render("website_event_track.track_view", values)

    @website.route(['/event/tracks/<model("event.event"):event>'], type='http', auth="public", multilang=True)
    def event_tracks(self, event, tag=None, **post):
        # TODO: filter on tracks: tags, search keywords
        values = {
            'event': event,
            'tracks': event.track_ids,
            'tags': event.track_tag_ids,
            'searches': {}
        }
        print 'ICI'
        return request.website.render("website_event_track.tracks", values)

    @website.route(['/event/detail/<model("event.event"):event>'], type='http', auth="public", multilang=True)
    def event_detail(self, event, **post):
        values = { 'event': event }
        return request.website.render("website_event_track.event_home", values)

    @website.route(['/event/track_proposal/<model("event.event"):event>'], type='http', auth="public", multilang=True)
    def event_detail(self, event=None, **post):
        values = { 'event': event }
        return request.website.render("website_event_track.event_track_proposal", values)

