# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden, NotFound

from odoo import exceptions, http
from odoo.http import request


class WebsiteEventTrackController(http.Controller):

    def _can_access_track(self, track_id):
        track = request.env['event.track'].browse(track_id).exists()
        if not track:
            raise NotFound()
        try:
            track.check_access_rule('read')
        except exceptions.AccessError:
            raise Forbidden()

        track_sudo = track.sudo()
        if not track_sudo.event_id.can_access_from_current_website():
            raise NotFound()

        return track_sudo

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
        track_sudo = self._can_access_track(track_id)

        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
        visitor_sudo._update_visitor_last_visit()

        force_create = set_reminder_on or track_sudo.wishlisted_by_default

        event_track_partner = track_sudo._get_event_track_visitors(visitor_sudo, force_create=force_create)

        if not track_sudo.wishlisted_by_default:
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
