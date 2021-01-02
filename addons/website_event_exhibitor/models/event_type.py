# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = "event.type"

    exhibitor_menu = fields.Boolean(
        string='Showcase Exhibitors', compute='_compute_exhibitor_menu',
        readonly=False, store=True,
        help='Display exhibitors on website')

    @api.depends('website_menu')
    def _compute_exhibitor_menu(self):
        for event_type in self:
            event_type.exhibitor_menu = event_type.website_menu
