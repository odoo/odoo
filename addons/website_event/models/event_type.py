# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _name = 'event.type'
    _inherit = ['event.type']

    website_menu = fields.Boolean('Display a dedicated menu on Website')
    community_menu = fields.Boolean(
        "Community Menu", compute="_compute_community_menu",
        readonly=False, store=True,
        help="Display community tab on website")
    menu_register_cta = fields.Boolean(
        'Add Register Button', compute='_compute_menu_register_cta',
        readonly=False, store=True)

    @api.depends('website_menu')
    def _compute_community_menu(self):
        for event_type in self:
            event_type.community_menu = event_type.website_menu

    @api.depends('website_menu')
    def _compute_menu_register_cta(self):
        for event_type in self:
            event_type.menu_register_cta = event_type.website_menu
