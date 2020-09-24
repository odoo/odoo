# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from datetime import timedelta
from pytz import timezone, utc
from werkzeug.exceptions import Forbidden, NotFound

import babel
import babel.dates
import base64
import pytz

from odoo import exceptions, http, fields, _
from odoo.http import request
from odoo.osv import expression
from odoo.tools import is_html_empty, plaintext2html


class EventTrackController(http.Controller):

    def _get_event_tracks_base_domain(self, event):
        """ Base domain for displaying tracks. Restrict to accepted or published
        tracks for people not managing events. Unpublished tracks may be displayed
        but not reachable for teasing purpose. """
        search_domain_base = [
            ('event_id', '=', event.id),
        ]
        if not request.env.user.has_group('event.group_event_user'):
            search_domain_base = expression.AND([
                search_domain_base,
                ['|', ('is_published', '=', True), ('is_accepted', '=', True)]
            ])
        return search_domain_base

    # ------------------------------------------------------------
    # TRACK LIST VIEW
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
            "website_event_track.tracks_session",
            self._event_tracks_get_values(event, tag=tag, **searches)
        )

    def _event_tracks_get_values(self, event, tag=None, **searches):
        # init and process search terms
        searches.setdefault('search', '')
        searches.setdefault('search_wishlist', '')
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

        # filter on wishlist (as post processing due to costly search on is_reminder_on)
        if searches.get('search_wishlist'):
            tracks_sudo = tracks_sudo.filtered(lambda track: track.is_reminder_on)

        # organize categories for display: announced, live, soon and day-based
        tracks_announced = tracks_sudo.filtered(lambda track: not track.date)
        tracks_wdate = tracks_sudo - tracks_announced
        date_begin_tz_all = list(set(
            dt.date()
            for dt in self._get_dt_in_event_tz(tracks_wdate.mapped('date'), event)
        ))
        date_begin_tz_all.sort()
        tracks_sudo_live = tracks_wdate.filtered(lambda track: track.is_published and track.is_track_live)
        tracks_sudo_soon = tracks_wdate.filtered(lambda track: track.is_published and not track.is_track_live and track.is_track_soon)
        tracks_by_day = []
        for display_date in date_begin_tz_all:
            matching_tracks = tracks_wdate.filtered(lambda track: self._get_dt_in_event_tz([track.date], event)[0].date() == display_date)
            tracks_by_day.append({'date': display_date, 'name': display_date, 'tracks': matching_tracks})
        if tracks_announced:
            tracks_announced = tracks_announced.sorted('wishlisted_by_default', reverse=True)
            tracks_by_day.append({'date': False, 'name': _('Coming soon'), 'tracks': tracks_announced})

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
            'today_tz': today_tz,
            # search information
            'searches': searches,
            'search_key': searches['search'],
            'search_wishlist': searches['search_wishlist'],
            'search_tags': search_tags,
            'tag_categories': tag_categories,
            # environment
            'is_html_empty': is_html_empty,
            'hostname': request.httprequest.host.split(':')[0],
            'user_event_manager': request.env.user.has_group('event.group_event_manager'),
        }

    # ------------------------------------------------------------
    # AGENDA VIEW
    # ------------------------------------------------------------

    @http.route(['''/event/<model("event.event"):event>/agenda'''], type='http', auth="public", website=True, sitemap=False)
    def event_agenda(self, event, tag=None, **post):
        if not event.can_access_from_current_website():
            raise NotFound()

        event = event.with_context(tz=event.date_tz or 'UTC')
        vals = {
            'event': event,
            'main_object': event,
            'tag': tag,
            'user_event_manager': request.env.user.has_group('event.group_event_manager'),
        }

        vals.update(self._prepare_calendar_values(event))

        return request.render("website_event_track.agenda_online", vals)

    def _prepare_calendar_values(self, event):
        """
         Override that should completely replace original method in v14.

        This methods slit the day (max end time - min start time) into 15 minutes time slots.
        For each time slot, we assign the tracks that start at this specific time slot, and we add the number
        of time slot that the track covers (track duration / 15 min)
        The calendar will be divided into rows of 15 min, and the talks will cover the corresponding number of rows
        (15 min slots).
        """
        event = event.with_context(tz=event.date_tz or 'UTC')
        local_tz = pytz.timezone(event.date_tz or 'UTC')
        lang_code = request.env.context.get('lang')
        event_track_ids = self._event_agenda_get_tracks(event)

        locations = list(set(track.location_id for track in event_track_ids))
        locations.sort(key=lambda x: x.id)

        # First split day by day (based on start time)
        time_slots_by_tracks = {track: self._split_track_by_days(track, local_tz) for track in event_track_ids}

        # extract all the tracks time slots
        track_time_slots = set().union(*(time_slot.keys() for time_slot in [time_slots for time_slots in time_slots_by_tracks.values()]))

        # extract unique days
        days = list(set(time_slot.date() for time_slot in track_time_slots))
        days.sort()

        # Create the dict that contains the tracks at the correct time_slots / locations coordinates
        tracks_by_days = dict.fromkeys(days, 0)
        time_slots_by_day = dict((day, dict(start=set(), end=set())) for day in days)
        tracks_by_rounded_times = dict((time_slot, dict((location, {}) for location in locations)) for time_slot in track_time_slots)
        for track, time_slots in time_slots_by_tracks.items():
            start_date = fields.Datetime.from_string(track.date).replace(tzinfo=pytz.utc).astimezone(local_tz)
            end_date = start_date + timedelta(hours=(track.duration or 0.25))

            for time_slot, duration in time_slots.items():
                tracks_by_rounded_times[time_slot][track.location_id][track] = {
                    'rowspan': duration,  # rowspan
                    'start_date': self._get_locale_time(start_date, lang_code),
                    'end_date': self._get_locale_time(end_date, lang_code),
                    'occupied_cells': self._get_occupied_cells(track, duration, locations, local_tz)
                }

                # get all the time slots by day to determine the max duration of a day.
                day = time_slot.date()
                time_slots_by_day[day]['start'].add(time_slot)
                time_slots_by_day[day]['end'].add(time_slot+timedelta(minutes=15*duration))
                tracks_by_days[day] += 1

        # split days into 15 minutes time slots
        global_time_slots_by_day = dict((day, {}) for day in days)
        for day, time_slots in time_slots_by_day.items():
            start_time_slot = min(time_slots['start'])
            end_time_slot = max(time_slots['end'])

            time_slots_count = int(((end_time_slot - start_time_slot).total_seconds() / 3600) * 4)
            current_time_slot = start_time_slot
            for i in range(0, time_slots_count + 1):
                global_time_slots_by_day[day][current_time_slot] = tracks_by_rounded_times.get(current_time_slot, {})
                global_time_slots_by_day[day][current_time_slot]['formatted_time'] = self._get_locale_time(current_time_slot, lang_code)
                current_time_slot = current_time_slot + timedelta(minutes=15)

        # count the number of tracks by days
        tracks_by_days = dict.fromkeys(days, 0)
        for track in event_track_ids:
            track_day = fields.Datetime.from_string(track.date).replace(tzinfo=pytz.utc).astimezone(local_tz).date()
            tracks_by_days[track_day] += 1

        return {
            'days': days,
            'tracks_by_days': tracks_by_days,
            'time_slots': global_time_slots_by_day,
            'locations': locations
        }

    def _event_agenda_get_tracks(self, event):
        tracks_sudo = event.sudo().track_ids.filtered(lambda track: track.date)
        if not request.env.user.has_group('event.group_event_manager'):
            tracks_sudo = tracks_sudo.filtered(lambda track: track.is_published or track.stage_id.is_accepted)
        return tracks_sudo

    def _get_locale_time(self, dt_time, lang_code):
        """ Get locale time from datetime object

            :param dt_time: datetime object
            :param lang_code: language code (eg. en_US)
        """
        locale = babel.Locale.parse(lang_code)
        return babel.dates.format_time(dt_time, format='short', locale=locale)

    def time_slot_rounder(self, time, rounded_minutes):
        """ Rounds to nearest hour by adding a timedelta hour if minute >= rounded_minutes
            E.g. : If rounded_minutes = 15 -> 09:26:00 becomes 09:30:00
                                              09:17:00 becomes 09:15:00
        """
        return (time.replace(second=0, microsecond=0, minute=0, hour=time.hour)
                + timedelta(minutes=rounded_minutes * (time.minute // rounded_minutes)))

    def _split_track_by_days(self, track, local_tz):
        """
        Based on the track start_date and the duration,
        split the track duration into :
            start_time by day : number of time slot (15 minutes) that the track takes on that day.
        E.g. :  start date = 01-01-2000 10:00 PM and duration = 3 hours
                return {
                    01-01-2000 10:00:00 PM: 8 (2 * 4),
                    01-02-2000 00:00:00 AM: 4 (1 * 4)
                }
        Also return a set of all the time slots
        """
        start_date = fields.Datetime.from_string(track.date).replace(tzinfo=pytz.utc).astimezone(local_tz)
        start_datetime = self.time_slot_rounder(start_date, 15)
        end_datetime = self.time_slot_rounder(start_datetime + timedelta(hours=(track.duration or 0.25)), 15)
        time_slots_count = int(((end_datetime - start_datetime).total_seconds() / 3600) * 4)

        time_slots_by_day_start_time = {start_datetime: 0}
        for i in range(0, time_slots_count):
            # If the new time slot is still on the current day
            next_day = (start_datetime + timedelta(days=1)).date()
            if (start_datetime + timedelta(minutes=15*i)).date() <= next_day:
                time_slots_by_day_start_time[start_datetime] += 1
            else:
                start_datetime = next_day.datetime()
                time_slots_by_day_start_time[start_datetime] = 0

        return time_slots_by_day_start_time

    def _get_occupied_cells(self, track, rowspan, locations, local_tz):
        """
        In order to use only once the cells that the tracks will occupy, we need to reserve those cells
        (time_slot, location) coordinate. Those coordinated will be given to the template to avoid adding
        blank cells where already occupied by a track.
        """
        occupied_cells = []

        start_date = fields.Datetime.from_string(track.date).replace(tzinfo=pytz.utc).astimezone(local_tz)
        start_date = self.time_slot_rounder(start_date, 15)
        for i in range(0, rowspan):
            time_slot = start_date + timedelta(minutes=15*i)
            if track.location_id:
                occupied_cells.append((time_slot, track.location_id))
            # when no location, reserve all locations
            else:
                occupied_cells += [(time_slot, location) for location in locations if location]

        return occupied_cells

    # ------------------------------------------------------------
    # TRACK PAGE VIEW
    # ------------------------------------------------------------

    @http.route('''/event/<model("event.event", "[('website_track', '=', True)]"):event>/track/<model("event.track", "[('event_id', '=', event.id)]"):track>''',
                type='http', auth="public", website=True, sitemap=True)
    def event_track_page(self, event, track, **options):
        track = self._fetch_track(track.id, allow_is_accepted=False)

        return request.render(
            "website_event_track.event_track_main",
            self._event_track_page_get_values(event, track.sudo(), **options)
        )

    def _event_track_page_get_values(self, event, track, **options):
        track = track.sudo()

        option_widescreen = options.get('widescreen', False)
        option_widescreen = bool(option_widescreen) if option_widescreen != '0' else False
        # search for tracks list
        tracks_other = track._get_track_suggestions(
            restrict_domain=self._get_event_tracks_base_domain(track.event_id),
            limit=10
        )

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
            'user_event_manager': request.env.user.has_group('event.group_event_manager'),
        }

    @http.route("/event/track/toggle_reminder", type="json", auth="public", website=True)
    def track_reminder_toggle(self, track_id, set_reminder_on):
        """ Set a reminder a track for current visitor. Track visitor is created or updated
        if it already exists. Exception made if un-wishlisting and no track_visitor
        record found (should not happen unless manually done).

        :param boolean set_reminder_on:
          If True, set as a wishlist, otherwise un-wishlist track;
          If the track is a Key Track (wishlisted_by_default):
            if set_reminder_on = False, blacklist the track_partner
            otherwise, un-blacklist the track_partner
        """
        track = self._fetch_track(track_id, allow_is_accepted=True)
        force_create = set_reminder_on or track.wishlisted_by_default
        event_track_partner = track._get_event_track_visitors(force_create=force_create)
        visitor_sudo = event_track_partner.visitor_id

        if not track.wishlisted_by_default:
            if not event_track_partner or event_track_partner.is_wishlisted == set_reminder_on:  # ignore if new state = old state
                return {'error': 'ignored'}
            event_track_partner.is_wishlisted = set_reminder_on
        else:
            if not event_track_partner or event_track_partner.is_blacklisted != set_reminder_on:  # ignore if new state = old state
                return {'error': 'ignored'}
            event_track_partner.is_blacklisted = not set_reminder_on

        result = {'reminderOn': set_reminder_on}
        if request.httprequest.cookies.get('visitor_uuid', '') != visitor_sudo.access_token:
            result['visitor_uuid'] = visitor_sudo.access_token

        return result

    # ------------------------------------------------------------
    # TRACK PROPOSAL
    # ------------------------------------------------------------

    @http.route(['''/event/<model("event.event"):event>/track_proposal'''], type='http', auth="public", website=True, sitemap=False)
    def event_track_proposal(self, event, **post):
        if not event.can_access_from_current_website():
            raise NotFound()

        return request.render("website_event_track.event_track_proposal", {'event': event, 'main_object': event})

    @http.route(['''/event/<model("event.event"):event>/track_proposal/post'''], type='http', auth="public", methods=['POST'], website=True)
    def event_track_proposal_post(self, event, **post):
        if not event.can_access_from_current_website():
            raise NotFound()

        tags = []
        for tag in event.allowed_track_tag_ids:
            if post.get('tag_' + str(tag.id)):
                tags.append(tag.id)

        track = request.env['event.track'].sudo().create({
            'name': post['track_name'],
            'partner_name': post['partner_name'],
            'partner_email': post['email_from'],
            'partner_phone': post['phone'],
            'partner_biography': plaintext2html(post['biography']),
            'event_id': event.id,
            'tag_ids': [(6, 0, tags)],
            'user_id': False,
            'description': plaintext2html(post['description']),
            'image': base64.b64encode(post['image'].read()) if post.get('image') else False
        })
        if request.env.user != request.website.user_id:
            track.sudo().message_subscribe(partner_ids=request.env.user.partner_id.ids)
        else:
            partner = request.env['res.partner'].sudo().search([('email', '=', post['email_from'])])
            if partner:
                track.sudo().message_subscribe(partner_ids=partner.ids)
        return request.render("website_event_track.event_track_proposal", {'track': track, 'event': event})

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _fetch_track(self, track_id, allow_is_accepted=False):
        track = request.env['event.track'].browse(track_id).exists()
        if not track:
            raise NotFound()
        try:
            track.check_access_rights('read')
            track.check_access_rule('read')
        except exceptions.AccessError:
            track_sudo = track.sudo()
            if allow_is_accepted and track_sudo.is_accepted:
                track = track_sudo
            else:
                raise Forbidden()

        event = track.event_id
        # JSON RPC have no website in requests
        if hasattr(request, 'website_id') and not event.can_access_from_current_website():
            raise NotFound()
        try:
            event.check_access_rights('read')
            event.check_access_rule('read')
        except exceptions.AccessError:
            raise Forbidden()

        return track

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
