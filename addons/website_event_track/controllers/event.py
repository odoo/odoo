# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.http import request


class EventOnlineController(WebsiteEventController):

    def _get_registration_confirm_values(self, event, attendees_sudo):
        values = super(EventOnlineController, self)._get_registration_confirm_values(event, attendees_sudo)
        values['hide_sponsors'] = True
        return values

    @http.route()
    def live_event_redirect(self, event):
        live_track = next((track for track in event.track_ids if track.is_track_live), None)
        if live_track:
            return request.redirect(live_track.website_url)
        return super().live_event_redirect(event)
