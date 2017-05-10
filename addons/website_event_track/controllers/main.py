# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel
import collections
import datetime
import pytz

from odoo import fields, http
from odoo.http import request
from odoo.tools import html_escape as escape, html2plaintext, pycompat


class WebsiteEventTrackController(http.Controller):

    @http.route(['''/event/<model("event.event"):event>/track/<model("event.track", "[('event_id','=',event[0])]"):track>'''], type='http', auth="public", website=True)
    def event_track_view(self, event, track, **post):
        track = track.sudo()
        values = {'track': track, 'event': track.event_id, 'main_object': track}
        return request.render("website_event_track.track_view", values)

    def _get_locale_time(self, dt_time, lang_code):
        """ Get locale time from datetime object

            :param dt_time: datetime object
            :param lang_code: language code (eg. en_US)
        """
        locale = babel.Locale.parse(lang_code)
        return babel.dates.format_time(dt_time, format='short', locale=locale)

    def _prepare_calendar(self, event, event_track_ids):
        local_tz = pytz.timezone(event.date_tz or 'UTC')
        lang_code = request.env.context.get('lang')
        locations = {}                  # { location: [track, start_date, end_date, rowspan]}
        dates = []                      # [ (date, {}) ]
        for track in event_track_ids:
            locations.setdefault(track.location_id or False, [])

        forcetr = True
        for track in event_track_ids:
            start_date = fields.Datetime.from_string(track.date).replace(tzinfo=pytz.utc).astimezone(local_tz)
            end_date = start_date + datetime.timedelta(hours=(track.duration or 0.5))
            location = track.location_id or False
            locations.setdefault(location, [])

            # New TR, align all events
            if forcetr or (start_date>dates[-1][0]) or not location:
                formatted_time = self._get_locale_time(start_date, lang_code)
                dates.append((start_date, {}, bool(location), formatted_time))
                for loc in list(locations):
                    if locations[loc] and (locations[loc][-1][2] > start_date):
                        locations[loc][-1][3] += 1
                    elif not locations[loc] or locations[loc][-1][2] <= start_date:
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

    @http.route(['''/event/<model("event.event", "[('website_track','=',1)]"):event>/agenda'''], type='http', auth="public", website=True)
    def event_agenda(self, event, tag=None, **post):
        days_tracks = collections.defaultdict(lambda: [])
        for track in event.track_ids.sorted(lambda track: (track.date, bool(track.location_id))):
            if not track.date:
                continue
            days_tracks[track.date[:10]].append(track)

        days = {}
        tracks_by_days = {}
        for day, tracks in pycompat.items(days_tracks):
            tracks_by_days[day] = tracks
            days[day] = self._prepare_calendar(event, tracks)

        return request.render("website_event_track.agenda", {
            'event': event,
            'days': days,
            'tracks_by_days': tracks_by_days,
            'tag': tag
        })

    @http.route([
        '''/event/<model("event.event", "[('website_track','=',1)]"):event>/track''',
        '''/event/<model("event.event", "[('website_track','=',1)]"):event>/track/tag/<model("event.track.tag"):tag>'''
        ], type='http', auth="public", website=True)
    def event_tracks(self, event, tag=None, **post):
        searches = {}
        if tag:
            searches.update(tag=tag.id)
            tracks = event.track_ids.filtered(lambda track: tag in track.tag_ids)
        else:
            tracks = event.track_ids

        values = {
            'event': event,
            'main_object': event,
            'tracks': tracks,
            'tags': event.tracks_tag_ids,
            'searches': searches,
            'html2plaintext': html2plaintext
        }
        return request.render("website_event_track.tracks", values)

    @http.route(['''/event/<model("event.event", "[('website_track_proposal','=',1)]"):event>/track_proposal'''], type='http', auth="public", website=True)
    def event_track_proposal(self, event, **post):
        return request.render("website_event_track.event_track_proposal", {'event': event})

    @http.route(['/event/<model("event.event"):event>/track_proposal/post'], type='http', auth="public", methods=['POST'], website=True)
    def event_track_proposal_post(self, event, **post):
        tags = []
        for tag in event.allowed_track_tag_ids:
            if post.get('tag_' + str(tag.id)):
                tags.append(tag.id)

        track = request.env['event.track'].sudo().create({
            'name': post['track_name'],
            'partner_name': post['partner_name'],
            'partner_email': post['email_from'],
            'partner_phone': post['phone'],
            'partner_biography': escape(post['biography']),
            'event_id': event.id,
            'tag_ids': [(6, 0, tags)],
            'user_id': False,
            'description': escape(post['description'])
        })
        if request.env.user != request.website.user_id:
            track.sudo().message_subscribe_users(user_ids=request.env.user.ids)
        else:
            partner = request.env['res.partner'].sudo().search([('email', '=', post['email_from'])])
            if partner:
                track.sudo().message_subscribe(partner_ids=partner.ids)
        return request.render("website_event_track.event_track_proposal_success", {'track': track, 'event': event})
