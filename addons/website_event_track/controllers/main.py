# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import datetime
import pytz
import re

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools import html_escape


class website_event(http.Controller):
    @http.route(['''/event/<model("event.event"):event>/track/<model("event.track", "[('event_id','=',event[0])]"):track>'''], type='http', auth="public", website=True)
    def event_track_view(self, event, track, **post):
        track_obj = request.registry.get('event.track')
        track = track_obj.browse(request.cr, openerp.SUPERUSER_ID, track.id, context=request.context)
        values = { 'track': track, 'event': track.event_id, 'main_object': track }
        return request.website.render("website_event_track.track_view", values)

    def _prepare_calendar(self, event, event_track_ids):
        local_tz = pytz.timezone(event.date_tz or 'UTC')
        locations = {}                  # { location: [track, start_date, end_date, rowspan]}
        dates = []                      # [ (date, {}) ]
        for track in event_track_ids:
            locations.setdefault(track.location_id or False, [])

        forcetr = True
        for track in event_track_ids:
            start_date = (datetime.datetime.strptime(track.date, '%Y-%m-%d %H:%M:%S')).replace(tzinfo=pytz.utc).astimezone(local_tz)
            end_date = start_date + datetime.timedelta(hours = (track.duration or 0.5))
            location = track.location_id or False
            locations.setdefault(location, [])

            # New TR, align all events
            if forcetr or (start_date>dates[-1][0]) or not location:
                dates.append((start_date, {}, bool(location)))
                for loc in locations.keys():
                    if locations[loc] and (locations[loc][-1][2] > start_date):
                        locations[loc][-1][3] += 1
                    elif not locations[loc] or locations[loc][-1][2] < start_date:
                        locations[loc].append([False, locations[loc] and locations[loc][-1][2] or dates[0][0], start_date, 1])
                        dates[-1][1][loc] = locations[loc][-1]
                forcetr = not bool(location)

            # Add event
            if locations[location] and locations[location][-1][1] > start_date:
                locations[location][-1][3] -= 1
            locations[location].append([track, start_date, end_date, 1])
            dates[-1][1][location] = locations[location][-1]
        return {
            'locations': locations,
            'dates': dates
        }


    # TODO: not implemented
    @http.route(['''/event/<model("event.event", "[('show_tracks','=',1)]"):event>/agenda'''], type='http', auth="public", website=True)
    def event_agenda(self, event, tag=None, **post):
        days_tracks = collections.defaultdict(lambda: [])
        for track in sorted(event.track_ids, key=lambda x: (x.date, bool(x.location_id))):
            if not track.date: continue
            days_tracks[track.date[:10]].append(track)

        days = {}
        days_tracks_count = {}
        for day, tracks in days_tracks.iteritems():
            days_tracks_count[day] = len(tracks)
            days[day] = self._prepare_calendar(event, tracks)

        cr, uid, context = request.cr, request.uid, request.context
        track_obj = request.registry['event.track']
        tracks_ids = track_obj.search(cr, openerp.SUPERUSER_ID, [('event_id', '=', event.id)], context=context)
        speakers = dict()
        for t in track_obj.browse(cr, openerp.SUPERUSER_ID, tracks_ids, context=context):
            acc = ""
            for speaker in t.speaker_ids:
                acc = speaker.name + u" – " + acc if acc else speaker.name
            speakers[t.id] = acc

        return request.website.render("website_event_track.agenda", {
            'event': event,
            'days': days,
            'days_nbr': days_tracks_count,
            'speakers': speakers,
            'tag': tag
        })

    @http.route([
        '''/event/<model("event.event", "[('show_tracks','=',1)]"):event>/track''',
        '''/event/<model("event.event", "[('show_tracks','=',1)]"):event>/track/tag/<model("event.track.tag"):tag>'''
        ], type='http', auth="public", website=True)
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

    @http.route(['''/event/<model("event.event", "[('show_track_proposal','=',1)]"):event>/track_proposal'''], type='http', auth="public", website=True)
    def event_track_proposal(self, event, **post):
        values = { 'event': event }
        return request.website.render("website_event_track.event_track_proposal", values)

    @http.route(['/event/<model("event.event"):event>/track_proposal/post'], type='http', auth="public", methods=['POST'], website=True)
    def event_track_proposal_post(self, event, **post):
        cr, uid, context = request.cr, request.uid, request.context

        tags = []
        for tag in event.allowed_track_tag_ids:
            if post.get('tag_'+str(tag.id)):
                tags.append(tag.id)

        track_obj = request.registry['event.track']
        track_id = track_obj.create(cr, openerp.SUPERUSER_ID, {
            'name': post['track_name'],
            'partner_name': post['partner_name'],
            'partner_email': post['email_from'],
            'partner_phone': post['phone'],
            'partner_biography': html_escape(post['biography']),
            'event_id': event.id,
            'tag_ids': [(6, 0, tags)],
            'user_id': False,
            'description': html_escape(post['description']),
        }, context=context)
        track = track_obj.browse(cr, uid, track_id, context=context)
        values = {'track': track, 'event': event}
        return request.website.render("website_event_track.event_track_proposal_success", values)
