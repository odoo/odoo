# -*- coding: utf-8 -*-
from odoo.addons import website_event_track
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventTrack(models.Model, website_event_track.EventTrack):
    _mailing_enabled = True

    def _mailing_get_default_domain(self, mailing):
        return [('stage_id.is_cancel', '=', False)]
