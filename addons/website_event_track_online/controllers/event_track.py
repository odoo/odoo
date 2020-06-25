# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden, NotFound

from odoo import exceptions, http
from odoo.http import request
from odoo.addons.website_event_track.controllers.main import WebsiteEventTrackController


class WebsiteEventTrackOnlineController(WebsiteEventTrackController):

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

    @http.route("/event/track/toggle_wishlist", type="json", auth="public", website=True)
    def track_wishlist_toggle(self, track_id, set_wishlisted):
        """ Wishlist a track for current visitor. Track visitor is created or updated
        if it already exists. Exception made if un-wishlisting and no track_visitor
        record found (should not happen unless manually done).

        :param boolean set_wishlisted: if True, set as a wishlist, otherwise un-whichlist
          track;
        """
        track_sudo = self._can_access_track(track_id)

        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
        visitor_sudo._update_visitor_last_visit()

        event_track_partner = track_sudo._get_event_track_visitors(visitor_sudo, force_create=set_wishlisted)
        if not event_track_partner or event_track_partner.is_wishlisted == set_wishlisted:  # ignore if new state = old state
            return {'error': 'ignored'}

        event_track_partner.is_wishlisted = set_wishlisted

        return {'wishlisted': set_wishlisted}
