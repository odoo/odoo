# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = "event.event"

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    # OVERRIDES: ADD SEQUENCE
    def _get_track_menu_entries(self):
        """ Remove agenda as this is now managed separately """
        self.ensure_one()
        return [
            (_('Talks'), '/event/%s/track' % slug(self), False, 10, 'track'),
            (_('Agenda'), '/event/%s/agenda' % slug(self), False, 70, 'track')
        ]

    def _get_track_proposal_menu_entries(self):
        """ See website_event_track._get_track_menu_entries() """
        self.ensure_one()
        return [(_('Talk Proposals'), '/event/%s/track_proposal' % slug(self), False, 15, 'track_proposal')]
