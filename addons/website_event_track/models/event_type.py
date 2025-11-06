# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    website_track = fields.Boolean(
        string='Tracks Agenda', compute='_compute_website_track_menu_data',
        help='Display the "Talks" and the "Agenda" tabs on website, redirecting to the list and the agenda of the talks.',
        readonly=False, store=True)
    website_track_proposal = fields.Boolean(
        string='Tracks Proposals', compute='_compute_website_track_menu_data',
        help='Display the "Propose a talk" tab on website, redirecting to the track proposal form.',
        readonly=False, store=True)

    @api.depends('website_menu')
    def _compute_website_track_menu_data(self):
        """ Simply activate or de-activate all menus at once. """
        for event_type in self:
            event_type.website_track = event_type.website_menu
            event_type.website_track_proposal = event_type.website_menu
