# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = "event.event"

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def _get_track_menu_entries(self):
        """ Talks are renamed to Sessions"""
        self.ensure_one()
        return [(_('Sessions'), '/event/%s/track' % slug(self), False, 10, 'track', False)]
