# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import website_event, event_booth


class EventType(website_event.EventType, event_booth.EventType):

    booth_menu = fields.Boolean(
        string='Booths on Website', compute='_compute_booth_menu',
        readonly=False, store=True)

    @api.depends('website_menu')
    def _compute_booth_menu(self):
        for event_type in self:
            event_type.booth_menu = event_type.website_menu
