# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event_track_session.controllers.session import WebsiteEventSessionController


class WebsiteEventSessionLiveController(WebsiteEventSessionController):

    def _event_tracks_get_values(self, event, tag=None, **searches):
        values = super(WebsiteEventSessionLiveController, self)._event_tracks_get_values(event, tag, **searches)
        values['viewers_count'] = values['tracks']._get_viewers_count()
        return values
