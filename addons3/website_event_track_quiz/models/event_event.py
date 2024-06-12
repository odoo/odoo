# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Event(models.Model):
    _inherit = "event.event"

    @api.depends("event_type_id", "website_menu", "community_menu")
    def _compute_community_menu(self):
        """ At type onchange: synchronize. At website_menu update: synchronize. """
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.community_menu = event.event_type_id.community_menu
            elif event.website_menu and (event.website_menu != event._origin.website_menu or not event.community_menu):
                event.community_menu = True
            elif not event.website_menu:
                event.community_menu = False
