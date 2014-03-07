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

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website as controllers
import datetime
import dateutil.parser as dparser
from collections import OrderedDict
import re
import werkzeug.utils

controllers = controllers()

class website_event(http.Controller):
    @http.route(['/event/<model("event.event"):event>/track/<model("event.track"):track>'], type='http', auth="public", website=True, multilang=True)
    def event_track_view(self, event, track, **post):
        track_obj = request.registry.get('event.track')
        track = track_obj.browse(request.cr, openerp.SUPERUSER_ID, track.id, context=request.context)
        values = { 'track': track, 'event': track.event_id, 'main_object': track }
        return request.website.render("website_event_track.track_view", values)

    # TODO: not implemented
    @http.route(['/event/<model("event.event"):event>/agenda/'], type='http', auth="public", website=True, multilang=True)
    def event_agenda(self, event, tag=None, **post):
        
        request.cr.execute('''
            Select id, location_id, groupby_datetime, duration, name, date from (
                Select id, location_id, to_char(date_trunc('hour',date),'mm-dd-yy hh AM') as
                groupby_datetime, duration, name, event_id, date, count(*) as tot from event_track
                group by event_id, duration, id, location_id, date, date_trunc('hour',date)
                order by date, date_trunc('hour',date)
            ) 
            event_query where event_query.event_id = %s 
                group by  event_query.location_id, event_query.id, 
                  event_query.groupby_datetime, event_query.duration,event_query.name, event_query.date;
            ''',(event.id,))
        
        fetch_tracks = request.cr.fetchall()
        unsort_tracks = {}
        room_list = []
        new_schedule = OrderedDict()
        location_object = request.registry.get('event.track.location')
        event_track_obj = request.registry.get('event.track')
        for track in fetch_tracks:
            room_list.append(track[1])
            if not unsort_tracks.has_key(track[2][:8]):
                unsort_tracks[track[2][:8]] = {}
            if not unsort_tracks[track[2][:8]].has_key(track[5]):
                unsort_tracks[track[2][:8]][track[5]] = []
            end_time = datetime.datetime.strptime(track[5], '%Y-%m-%d %H:%M:%S') + datetime.timedelta(minutes = int(track[3]))
            new_schedule[track[0]] = {'time': track[5],'end_time': end_time}
            speaker = event_track_obj.browse(request.cr, request.uid, track[0], context=request.context)['speaker_ids']
            unsort_tracks[track[2][:8]][track[5]].append({
                             'id': track[0],
                             'title': track[4],
                             'time': track[5],
                             'location_id': track[1],
                             'duration':track[3],
                             'location_id': track[1],
                             'end_time': end_time,
                             'speaker_ids': [s.name for s in speaker],
                       })
        #Get All Locations
        room_list = list(set(room_list))
        room_list.sort()
        rooms = []
        for room in room_list:
            if room:rooms.append([room, location_object.browse(request.cr, openerp.SUPERUSER_ID, room).name])
        
        sort_track = {}
        
        for track in unsort_tracks.keys():
            sorted_key = sorted(unsort_tracks[track].keys() ,key=lambda x: (dparser.parse(x)).strftime('%a, %d %b %Y %H:%M:%S'))
            sort_track[track] = OrderedDict()
            for tra in sorted_key:
                sort_track[track][tra] = sorted(unsort_tracks[track][tra], key=lambda x: x['location_id'])
        
        values = {
            'event': event,
            'main_object': event,
            'room_list': rooms,
            'days': sort_track,
        }
        return request.website.render("website_event_track.agenda", values)

    @http.route([
        '/event/<model("event.event"):event>/track/',
        '/event/<model("event.event"):event>/track/tag/<model("event.track.tag"):tag>'
        ], type='http', auth="public", website=True, multilang=True)
    def event_tracks(self, event, tag=None, **post):
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

    @http.route(['/event/<model("event.event"):event>/track_proposal/'], type='http', auth="public", website=True, multilang=True)
    def event_track_proposal(self, event, **post):
        values = { 'event': event }
        return request.website.render("website_event_track.event_track_proposal", values)

    @http.route(['/event/<model("event.event"):event>/track_proposal/post'], type='http', auth="public", methods=['POST'], website=True, multilang=True)
    def event_track_proposal_post(self, event, **post):
        cr, uid, context = request.cr, request.uid, request.context

        tobj = request.registry['event.track']

        tags = []
        for tag in event.allowed_track_tag_ids:
            if post.get('tag_'+str(tag.id)):
                tags.append(tag.id)

        e = werkzeug.utils.escape
        track_description = '''<section data-snippet-id="text-block">
    <div class="container">
        <div class="row">
            <div class="col-md-12 text-center">
                <h2>%s</h2>
            </div>
            <div class="col-md-12">
                <p>%s</p>
            </div>
            <div class="col-md-12">
                <h3>About The Author</h3>
                <p>%s</p>
            </div>
        </div>
    </div>
</section>''' % (e(post['track_name']), 
            e(post['description']), e(post['biography']))

        track_id = tobj.create(cr, openerp.SUPERUSER_ID, {
            'name': post['track_name'],
            'event_id': event.id,
            'tag_ids': [(6, 0, tags)],
            'user_id': False,
            'description': track_description
        }, context=context)

        tobj.message_post(cr, openerp.SUPERUSER_ID, [track_id], body="""Proposed By: %s<br/>
          Mail: <a href="mailto:%s">%s</a><br/>
          Phone: %s""" % (e(post['partner_name']), e(post['email_from']), 
            e(post['email_from']), e(post['phone'])), context=context)

        track = tobj.browse(cr, uid, track_id, context=context)
        values = {'track': track, 'event':event}
        return request.website.render("website_event_track.event_track_proposal_success", values)
