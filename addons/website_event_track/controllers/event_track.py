# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from collections import defaultdict
from datetime import timedelta
from pytz import timezone, utc
from werkzeug.exceptions import Forbidden, NotFound

import babel
import babel.dates
import base64
import json
import operator
import pytz

from odoo import http, fields, tools, _
from odoo.fields import Domain
from odoo.http import content_disposition, request
from odoo.tools import is_html_empty, plaintext2html
from odoo.tools.misc import babel_locale_parse


class EventTrackController(http.Controller):

    def _get_event_tracks_agenda_domain(self, event):
        """ Base domain for displaying track names (preview). The returned search
        domain will select the tracks that belongs to a track stage that should
        be visible in the agenda (see: 'is_visible_in_agenda'). Published tracks
        are also displayed whatever their stage. """
        agenda_domain = [
            '&',
            ('event_id', '=', event.id),
            '|',
            ('is_published', '=', True),
            ('stage_id.is_visible_in_agenda', '=', True),
        ]
        return agenda_domain

    def _get_event_tracks_domain(self, event):
        """ Base domain for displaying tracks. The returned search domain will
        select the tracks that belongs to a track stage that should be visible
        in the agenda (see: 'is_visible_in_agenda'). When the user is a visitor,
        the domain will contain an additional condition that will remove the
        unpublished tracks from the search results."""
        search_domain_base = self._get_event_tracks_agenda_domain(event)
        if not request.env.user.has_group('event.group_event_registration_desk'):
            search_domain_base = Domain.AND([
                search_domain_base,
                [('is_published', '=', True)]
            ])
        return search_domain_base

    # ------------------------------------------------------------
    # TRACK LIST VIEW
    # ------------------------------------------------------------

    @http.route([
        '''/event/<model("event.event"):event>/track''',
        '''/event/<model("event.event"):event>/track/tag/<model("event.track.tag"):tag>'''
    ], type='http', auth="public", website=True, sitemap=False, readonly=True)
    def event_tracks(self, event, tag=None, **searches):
        """ Main route

        :param event: event whose tracks are about to be displayed;
        :param tag: deprecated: search for a specific tag
        :param searches: frontend search dict, containing

          * 'search': search string;
          * 'tags': list of tag IDs for filtering;
        """

        if searches.get('tags', '[]').count(',') > 0 and request.httprequest.method == 'GET':
            # Previously, the tags were searched using GET, which caused issues with crawlers (too many hits)
            # We replaced those with POST to avoid that, but it's not sufficient as bots "remember" crawled pages for a while
            # This permanent redirect is placed to instruct the bots that this page is no longer valid
            # Note: We allow a single tag to be GET, to keep crawlers & indexes on those pages
            # What we really want to avoid is combinatorial explosions
            # (Tags are formed as a JSON array, so we count ',' to keep it simple)
            slug = request.env['ir.http']._slug
            return request.redirect(f'/event/{slug(event)}/track', code=301)
        seo_object = event.track_menu_ids.filtered(lambda menu: menu.menu_id.url.endswith('/track'))

        return request.render(
            "website_event_track.tracks_session",
            self._event_tracks_get_values(event, tag=tag, **searches) | {'seo_object': seo_object}
        )

    def _event_tracks_get_values(self, event, tag=None, **searches):
        # init and process search terms
        searches.setdefault('search', '')
        searches.setdefault('search_wishlist', '')
        searches.setdefault('tags', '')
        search_domain = self._get_event_tracks_agenda_domain(event)

        # search on content
        if searches.get('search'):
            search_domain = Domain.AND([
                search_domain,
                ['|', ('name', 'ilike', searches['search']), ('partner_name', 'ilike', searches['search'])]
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
            search_domain = Domain.AND([
                search_domain,
                *search_domain_items
            ])

        # fetch data to display with TZ set for both event and tracks
        now_tz = utc.localize(fields.Datetime.now().replace(microsecond=0), is_dst=False).astimezone(timezone(event.date_tz))
        today_tz = now_tz.date()
        event = event.with_context(tz=event.date_tz or 'UTC')
        tracks_sudo = event.env['event.track'].sudo().search(search_domain, order='is_published desc, date asc')
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
        tracks_sudo_live = tracks_wdate.filtered(lambda track: track.is_track_live)
        tracks_sudo_soon = tracks_wdate.filtered(lambda track: not track.is_track_live and track.is_track_soon)
        tracks_by_day = []
        for display_date in date_begin_tz_all:
            matching_tracks = tracks_wdate.filtered(lambda track: self._get_dt_in_event_tz([track.date], event)[0].date() == display_date)
            tracks_by_day.append({'date': display_date, 'name': display_date, 'tracks': matching_tracks})
        if tracks_announced:
            tracks_announced = tracks_announced.sorted('wishlisted_by_default', reverse=True)
            tracks_by_day.append({'date': False, 'name': _('Coming soon'), 'tracks': tracks_announced})
        # Check if there are any ongoing or upcoming tracks
        has_upcoming_or_ongoing = any(track for track in tracks_sudo if not track.is_track_done)

        for tracks_group in tracks_by_day:
           tracks_group['default_collapsed'] = (
                has_upcoming_or_ongoing and
                tracks_group['date'] and all(track.is_track_done for track in tracks_group['tracks'])
            )

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
            'search_count': len(tracks_sudo),
            'search_key': searches['search'],
            'search_wishlist': searches['search_wishlist'],
            'search_tags': search_tags,
            'tag_categories': tag_categories,
            # environment
            'is_html_empty': is_html_empty,
            'hostname': request.httprequest.host.split(':')[0],
            'is_event_user': request.env.user.has_group('event.group_event_user'),
            'website_visitor_timezone': request.env['website.visitor']._get_visitor_timezone(),
        }

    # ------------------------------------------------------------
    # AGENDA VIEW
    # ------------------------------------------------------------

    @http.route(['''/event/<model("event.event"):event>/agenda'''], type='http', auth="public", website=True, sitemap=False)
    def event_agenda(self, event, tag=None, **post):
        event = event.with_context(tz=event.date_tz or 'UTC')
        seo_object = event.track_menu_ids.filtered(lambda menu: menu.menu_id.url.endswith('/agenda'))
        vals = {
            'event': event,
            'main_object': event,
            'seo_object': seo_object,
            'tag': tag,
            'is_event_user': request.env.user.has_group('event.group_event_user'),
            'website_visitor_timezone': request.env['website.visitor']._get_visitor_timezone(),
        }

        vals.update(self._prepare_calendar_values(event))

        return request.render("website_event_track.agenda_online", vals)

    def _prepare_calendar_values(self, event):
        """ This methods slit the day (max end time - min start time) into
        15 minutes time slots. For each time slot, we assign the tracks that
        start at this specific time slot, and we add the number of time slot
        that the track covers (track duration / 15 min). The calendar will be
        divided into rows of 15 min, and the talks will cover the corresponding
        number of rows (15 min slots). """
        event = event.with_context(tz=event.date_tz or 'UTC')
        local_tz = pytz.timezone(event.date_tz or 'UTC')
        lang_code = request.env.context.get('lang')

        base_track_domain = Domain.AND([
            self._get_event_tracks_agenda_domain(event),
            [('date', '!=', False)]
        ])
        tracks_sudo = request.env['event.track'].sudo().search(base_track_domain)

        locations = list(set(track.location_id for track in tracks_sudo))
        locations.sort(key=operator.itemgetter('sequence', 'id'))

        # First split day by day (based on start time)
        time_slots_by_tracks = {track: self._split_track_by_days(track, local_tz) for track in tracks_sudo}

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
            for _i in range(0, time_slots_count + 1):
                global_time_slots_by_day[day][current_time_slot] = tracks_by_rounded_times.get(current_time_slot, {})
                global_time_slots_by_day[day][current_time_slot]['formatted_time'] = self._get_locale_time(current_time_slot, lang_code)
                current_time_slot = current_time_slot + timedelta(minutes=15)

        # count the number of tracks by days
        tracks_by_days = dict.fromkeys(days, 0)
        locations_by_days = defaultdict(list)
        for track in tracks_sudo:
            track_day = fields.Datetime.from_string(track.date).replace(tzinfo=pytz.utc).astimezone(local_tz).date()
            tracks_by_days[track_day] += 1
            if track.location_id not in locations_by_days[track_day]:
                locations_by_days[track_day].append(track.location_id)

        for used_locations in locations_by_days.values():
            used_locations.sort(key=operator.itemgetter('sequence', 'id'))

        return {
            'days': days,
            'tracks_by_days': tracks_by_days,
            'locations_by_days': locations_by_days,
            'time_slots': global_time_slots_by_day,
            'locations': locations  # TODO: clean me in master, kept for retro-compatibility
        }

    def _get_locale_time(self, dt_time, lang_code):
        """ Get locale time from datetime object

            :param dt_time: datetime object
            :param lang_code: language code (eg. en_US)
        """
        locale = babel_locale_parse(lang_code)
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
                type='http', auth="public", website=True, sitemap=True, readonly=True)
    def event_track_page(self, event, track, **options):
        track = self._fetch_track(track.id, allow_sudo=False)

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
            restrict_domain=self._get_event_tracks_domain(track.event_id),
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
            'is_event_user': request.env.user.has_group('event.group_event_user'),
            'user_event_manager': request.env.user.has_group('event.group_event_manager'),
            'website_visitor_timezone': request.env['website.visitor']._get_visitor_timezone(),
        }

    @http.route("/event/track/toggle_reminder", type="jsonrpc", auth="public", website=True)
    def track_reminder_toggle(self, track_id, set_reminder_on):
        """ Set a reminder a track for current visitor. Track visitor is created or updated
        if it already exists. Exception made if un-favoriting and no track_visitor
        record found (should not happen unless manually done).

        :param boolean set_reminder_on:
          If True, set as a favorite, otherwise un-favorite track;
          If the track is a Key Track (wishlisted_by_default):
            if set_reminder_on = False, blacklist the track_partner
            otherwise, un-blacklist the track_partner
        """
        track = self._fetch_track(track_id, allow_sudo=True)
        force_create = set_reminder_on or track.wishlisted_by_default
        event_track_partner = track._get_event_track_visitors(force_create=force_create)

        if not track.wishlisted_by_default:
            if not event_track_partner or event_track_partner.is_wishlisted == set_reminder_on:  # ignore if new state = old state
                return {'error': 'ignored'}
            event_track_partner.is_wishlisted = set_reminder_on
        else:
            if not event_track_partner or event_track_partner.is_blacklisted != set_reminder_on:  # ignore if new state = old state
                return {'error': 'ignored'}
            event_track_partner.is_blacklisted = not set_reminder_on

        result = {'reminderOn': set_reminder_on}

        return result

    @http.route('/event/track/send_email_reminder', type="jsonrpc", auth="public", website=True)
    def send_email_reminder(self, track_id, email_to):
        """ Send email, to email_to if the user is public otherwise to the user email address,
        with tracks' reminders for external calendars. """
        template = self.env.ref("website_event_track.mail_template_data_track_reminder", raise_if_not_found=False)
        if not template:
            return {'success': False, 'error': 'missing_template'}

        track_su = self.env['event.track'].sudo().browse(track_id)
        # Check that the visitor has the permission to read the track on the website.
        track = track_su.filtered_domain(self._get_event_tracks_domain(track_su.event_id))
        valid_email_to = tools.email_normalize(email_to if request.env.user._is_public() else request.env.user.email)
        error_message = ''
        if not track:
            error_message = _('Invalid data.')
        elif not valid_email_to:
            error_message = _('Invalid email.')
        elif track.is_track_done or track.event_id.is_finished:
            error_message = _('The talk is already finished.')
        elif not track.is_track_upcoming:
            error_message = _('The talk has already begun.')
        if error_message:
            return {'success': False, 'message': error_message}

        template.sudo().with_context(
            lang=request.cookies.get('frontend_lang') if request.env.user._is_public() else request.env.context.get('lang', request.env.user.lang)
        ).send_mail(track.id, email_values={'email_to': valid_email_to})
        return {'success': True}

    # ------------------------------------------------------------
    # TRACK PROPOSAL
    # ------------------------------------------------------------

    @http.route(['''/event/<model("event.event"):event>/track_proposal'''], type='http', auth="public", website=True, sitemap=False)
    def event_track_proposal(self, event, **post):
        return request.render("website_event_track.event_track_proposal", {
            'event': event,
            'main_object': event,
            'seo_object': event.track_proposal_menu_ids,
        })

    @http.route(['''/event/<model("event.event"):event>/track_proposal/post'''], type='http', auth="public", methods=['POST'], website=True)
    def event_track_proposal_post(self, event, **post):
        if not event.can_access_from_current_website():
            return json.dumps({'error': 'forbidden'})

        # Only accept existing tag indices. Use search instead of browse + exists:
        # this prevents users to register colorless tags if not allowed to (ACL).
        input_tag_indices = [int(tag_id) for tag_id in post['tags'].split(',') if tag_id]
        valid_tag_indices = request.env['event.track.tag'].search([('id', 'in', input_tag_indices)]).ids

        contact = request.env['res.partner']
        visitor_partner = request.env['website.visitor']._get_visitor_from_request().partner_id
        # Contact name is required. Therefore, empty contacts are not considered here. At least one of contact_phone
        # and contact_email must be filled. Email is verified. If the post tries to create contact with no valid entry,
        # raise exception. If normalized email is the same as logged partner, use its partner_id on track instead.
        # This prevents contact duplication. Otherwise, create new contact with contact additional info of post.
        if post.get('add_contact_information'):
            valid_contact_email = tools.email_normalize(post.get('contact_email'))
            # Here, the phone is not formatted. To format it, one needs a country. Based on a country, from geoip for instance.
            # The problem is that one could propose a track in country A with phone number of country B. Validity is therefore
            # quite tricky. We accept any format of contact_phone. Could be improved with select country phone widget.
            if valid_contact_email or post.get('contact_phone'):
                if visitor_partner and valid_contact_email == visitor_partner.email_normalized:
                    contact = visitor_partner
                else:
                    contact = request.env['res.partner'].sudo().create({
                        'email': valid_contact_email,
                        'name': post.get('contact_name'),
                        'phone': post.get('contact_phone'),
                    })
            else:
                return json.dumps({'error': 'invalidFormInputs'})
        # If the speaker email is the same as logged user's, then also uses its partner on track, same as above.
        else:
            valid_speaker_email = tools.email_normalize(post['partner_email'])
            if visitor_partner and valid_speaker_email == visitor_partner.email_normalized:
                contact = visitor_partner

        track = request.env['event.track'].with_context({'mail_create_nosubscribe': True}).sudo().create({
            'name': post['track_name'],
            'partner_id': contact.id,
            'partner_name': post['partner_name'],
            'partner_email': post['partner_email'],
            'partner_phone': post['partner_phone'],
            'partner_function': post['partner_function'],
            'contact_phone': contact.phone,
            'contact_email': contact.email,
            'event_id': event.id,
            'tag_ids': [(6, 0, valid_tag_indices)],
            'description': plaintext2html(post['description']),
            'partner_biography': plaintext2html(post['partner_biography']),
            'user_id': False,
            'image': base64.b64encode(post['image'].read()) if post.get('image') else False,
        })

        if request.env.user != request.website.user_id:
            track.sudo().message_subscribe(partner_ids=request.env.user.partner_id.ids)

        return json.dumps({'success': True})

    # ACL : This route is necessary since rpc search_read method in js is not accessible to all users (e.g. public user).
    @http.route(['''/event/track_tag/search_read'''], type='jsonrpc', auth="public", website=True)
    def website_event_track_fetch_tags(self, domain, fields):
        return request.env['event.track.tag'].search_read(domain, fields)

    # ------------------------------------------------------------
    # HELPERS ROUTES
    # ------------------------------------------------------------

    @http.route(['''/event/<model("event.event"):event>/track/<model("event.track"):track>/ics'''], type='http', auth="public")
    def event_track_ics_file(self, event, track):
        lang = request.env.context.get('lang', request.env.user.lang)
        if request.env.user._is_public():
            lang = request.cookies.get('frontend_lang')
        track = track.with_context(lang=lang)
        files = track._get_ics_file()
        content = files.get(track.id)
        if not content:
            return NotFound()
        return request.make_response(content, [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(f'{event.name}-{track.name}.ics'))
        ])

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _fetch_track(self, track_id, allow_sudo=False):
        track = request.env['event.track'].browse(track_id).exists()
        if not track:
            raise NotFound()
        if not track.has_access('read'):
            if not allow_sudo:
                raise Forbidden()
            track = track.sudo()

        event = track.event_id
        # JSON RPC have no website in requests
        if hasattr(request, 'website_id') and not event.can_access_from_current_website():
            raise NotFound()
        if not event.has_access('read'):
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
