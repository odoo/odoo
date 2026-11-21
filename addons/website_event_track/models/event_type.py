# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    website_track = fields.Boolean(
        string='Tracks on Website', compute='_compute_website_track_menu_data',
        readonly=False, store=True)
    website_track_proposal = fields.Boolean(
        string='Tracks Proposals on Website', compute='_compute_website_track_menu_data',
        readonly=False, store=True)
    track_stage_ids = fields.Many2many(
        'event.track.stage', 'event_track_stage_event_type_rel', 'event_type_id', 'stage_id',
        string='Track Stages',
        help="Track stages given to events created from this template. If empty, "
             "events get the default track stages.")

    @api.depends('website_menu')
    def _compute_website_track_menu_data(self):
        """ Simply activate or de-activate all menus at once. """
        for event_type in self:
            event_type.website_track = event_type.website_menu
            event_type.website_track_proposal = event_type.website_menu
