# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.addons.website_event_track.controllers.event_track import EventTrackController
from odoo.http import request


class WebsiteEventSessionLiveController(EventTrackController):

    def _event_track_page_get_values(self, event, track, **options):
        if 'widescreen' not in options:
            options['widescreen'] = track.youtube_video_url and (track.is_youtube_replay or track.is_track_soon or track.is_track_live or track.is_track_done)
        values = super(WebsiteEventSessionLiveController, self)._event_track_page_get_values(event, track, **options)
        # Youtube disables the chat embed on all mobile devices
        # This regex is a naive attempt at matching their behavior (should work for most cases)
        values['is_mobile_chat_disabled'] = bool(re.match(
            r'^.*(Android|iPad|iPhone).*',
            request.httprequest.headers.get('User-Agent', request.httprequest.headers.get('user-agent', ''))))
        return values
