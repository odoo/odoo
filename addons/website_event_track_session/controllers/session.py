# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from pytz import timezone, utc
from werkzeug.exceptions import Forbidden, NotFound

from odoo import exceptions, fields, http
from odoo.addons.website_event_track.controllers.main import WebsiteEventTrackController
from odoo.http import request
from odoo.osv import expression
from odoo.tools import is_html_empty


class WebsiteEventSessionController(WebsiteEventTrackController):

    def _get_event_tracks_base_domain(self, event):
        """ Base domain for displaying tracks. Restrict to accepted tracks for
        people not managing events. Unpublished tracks may be displayed for teasing
        purpose. """
        search_domain_base = [
            ('event_id', '=', event.id),
        ]
        if not request.env.user.has_group('event.group_event_user'):
            search_domain_base = expression.AND([search_domain_base, [('is_accepted', '=', True)]])
        return search_domain_base

    # ------------------------------------------------------------
    # MAIN PAGE
    # ------------------------------------------------------------

    @http.route([
        '''/event/<model("event.event"):event>/track''',
        '''/event/<model("event.event"):event>/track/tag/<model("event.track.tag"):tag>'''
    ], type='http', auth="public", website=True, sitemap=False)
    def event_tracks(self, event, tag=None, **searches):
        """ Main route

        :param event: event whose tracks are about to be displayed;
        :param tag: deprecated: search for a specific tag
        :param searches: frontend search dict, containing

          * 'search': search string;
          * 'tags': list of tag IDs for filtering;
        """
        if not event.can_access_from_current_website():
            raise NotFound()

        return request.render(
            "website_event_track.tracks",
            self._event_tracks_get_values(event, tag=tag, **searches)
        )

    def _event_tracks_get_values(self, event, tag=None, **searches):
        # init and process search terms
        searches.setdefault('search', '')
        searches.setdefault('tags', '')
        search_domain = self._get_event_tracks_base_domain(event)

        # search on content
        if searches.get('search'):
            search_domain = expression.AND([
                search_domain,
                [('name', 'ilike', searches['search'])]
            ])

        # search on tags
        search_tags = self._get_search_tags(searches['tags'])
        if not search_tags and tag:  # backward compatibility
            search_tags = tag
        if search_tags:
            # Example: You filter on age: 10-12 and activity: football.
            # Doing it this way allows to only get events who are tagged "age: 10-12" AND "activity: football".
            # Add another tag "age: 12-15" to the search and it would fetch the ones who are tagged:
            # ("age: 10-12" OR "age: 12-15") AND "activity: football
            grouped_tags = dict()
            for search_tag in search_tags:
                grouped_tags.setdefault(search_tag.category_id, list()).append(search_tag)
            search_domain_items = [
                [('tag_ids', 'in', [tag.id for tag in grouped_tags[group]])]
                for group in grouped_tags
            ]
            search_domain = expression.AND([
                search_domain,
                *search_domain_items
            ])

        # fetch data to display with TZ set for both event and tracks
        now_tz = utc.localize(fields.Datetime.now().replace(microsecond=0), is_dst=False).astimezone(timezone(event.date_tz))
        today_tz = now_tz.date()
        event = event.with_context(tz=event.date_tz or 'UTC')
        tracks_sudo = event.env['event.track'].sudo().search(search_domain, order='date asc')
        tag_categories = request.env['event.track.tag.category'].sudo().search([])

        # organize categories for display: live, soon and day-based
        date_begin_tz_all = list(set(
            dt.date()
            for dt in self._get_dt_in_event_tz(tracks_sudo.mapped('date'), event)
        ))
        date_begin_tz_all.sort(key=lambda date: (date < today_tz, date), reverse=False)
        tracks_sudo_live = tracks_sudo.filtered(lambda track: track.is_published and track.is_track_live)
        tracks_sudo_soon = tracks_sudo.filtered(lambda track: track.is_published and not track.is_track_live and track.is_track_soon)
        tracks_by_day = []
        for display_date in date_begin_tz_all:
            matching_track = tracks_sudo.filtered(lambda track: self._get_dt_in_event_tz([track.date], event)[0].date() == display_date)
            sorted_tracks = matching_track.sorted(lambda track: track.is_track_done)
            tracks_by_day.append((display_date, sorted_tracks))

        # return rendering values
        return {
            # event information
            'event': event,
            'main_object': event,
            # tracks display information
            'tracks': tracks_sudo,
            'tracks_by_day': tracks_by_day,
            'tracks_live': tracks_sudo_live,
            'tracks_soon': tracks_sudo_soon,
            # search information
            'searches': searches,
            'search_key': searches['search'],
            'search_tags': search_tags,
            'tag_categories': tag_categories,
            # environment
            'is_html_empty': is_html_empty,
            'hostname': request.httprequest.host.split(':')[0],
            'user_event_manager': request.env.user.has_group('event.group_event_manager'),
        }

    # ------------------------------------------------------------
    # PAGE VIEW
    # ------------------------------------------------------------

    @http.route(['/event/<model("event.event"):event>/track/<model("event.track"):track>'],
                 type='http', auth="public", website=True, sitemap=False)
    def event_track(self, event, track, **options):
        if not event.can_access_from_current_website():
            raise NotFound()

        try:
            track.check_access_rule('read')
        except exceptions.AccessError:
            raise Forbidden()

        return request.render(
            "website_event_track_session.event_track_main",
            self._event_track_get_values(event, track, **options)
        )

    def _event_track_get_values(self, event, track, **options):
        track = track.sudo()

        # search for tracks list
        search_domain_base = self._get_event_tracks_base_domain(event)
        search_domain_base = expression.AND([
            search_domain_base,
            ['&', ('is_published', '=', True), ('id', '!=', track.id)]
        ])
        tracks_other = track._get_track_suggestions()

        option_widescreen = options.get('widescreen', False)
        option_widescreen = bool(option_widescreen) if option_widescreen != '0' else False

        return {
            # event information
            'event': event,
            'main_object': track,
            'track': track,
            # sidebar
            'tracks_other': tracks_other,
            # options
            'option_widescreen': option_widescreen,
            # environment
            'is_html_empty': is_html_empty,
            'hostname': request.httprequest.host.split(':')[0],
        }

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _get_search_tags(self, tag_search):
        # TDE FIXME: make me generic (slides, event, ...)
        try:
            tag_ids = literal_eval(tag_search)
        except Exception:
            tags = request.env['event.track.tag'].sudo()
        else:
            # perform a search to filter on existing / valid tags implicitly
            tags = request.env['event.track.tag'].sudo().search([('id', 'in', tag_ids)])
        return tags

    def _get_dt_in_event_tz(self, datetimes, event):
        tz_name = event.date_tz
        return [
            utc.localize(dt, is_dst=False).astimezone(timezone(tz_name))
            for dt in datetimes
        ]
