# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event_track_session.controllers.session import WebsiteEventSessionController


class WebsiteEventSessionLiveController(WebsiteEventSessionController):

    def _event_track_get_values(self, event, track, **options):
        if 'widescreen' not in options:
            options['widescreen'] = bool(track.youtube_video_url)
        return super(WebsiteEventSessionLiveController, self)._event_track_get_values(event, track, **options)
