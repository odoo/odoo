# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden, NotFound

from odoo import exceptions, http
from odoo.addons.website_event_track.controllers.main import WebsiteEventTrackController
from odoo.http import request


class EventTrackOnlineController(WebsiteEventTrackController):

    def _event_agenda_get_tracks(self, event):
        tracks_sudo = event.sudo().track_ids
        if not request.env.user.has_group('event.group_event_manager'):
            tracks_sudo = tracks_sudo.filtered(lambda track: track.is_published or track.stage_id.is_accepted)
        return tracks_sudo

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
