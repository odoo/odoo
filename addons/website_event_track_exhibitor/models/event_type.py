# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = "event.type"

    menu_exhibitor = fields.Boolean(
        string='Exhibitors on Website', compute='_compute_menu_exhibitor',
        readonly=False, store=True)

    @api.depends('website_menu')
    def _compute_menu_exhibitor(self):
        for event_type in self:
            if not event_type.website_menu:
                event_type.menu_exhibitor = False
