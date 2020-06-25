# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = "event.event"

    def _get_track_menu_entries(self):
        """ Talks are renamed to Sessions in online mode as it is accurater. """
        self.ensure_one()
        menu_entries = super(EventEvent, self)._get_track_menu_entries()
        updated = []
        for entry in menu_entries:
            if '/track' not in entry[1]:
                updated.append(entry)
            else:
                updated.append((_('Sessions'), '/event/%s/track' % slug(self), False, 'track'))
        return updated
