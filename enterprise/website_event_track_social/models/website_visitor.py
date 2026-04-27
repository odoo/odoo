# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteVisitor(models.Model):
    _name = 'website.visitor'
    _inherit = 'website.visitor'

    event_track_push_enabled_ids = fields.Many2many(
        'event.track', string="Push Enabled Tracks",
        help="Tracks that are 'default favorited' can be blacklisted and the visitor is removed from push reminders.",
        compute="_compute_event_track_push_enabled_ids", compute_sudo=True,
        search="_search_event_track_push_enabled_ids",
        groups="event.group_event_user")

    @api.depends('event_track_visitor_ids.track_id')
    def _compute_event_track_push_enabled_ids(self):
        results = self.env['event.track.visitor']._read_group(
            [('visitor_id', 'in', self.ids), ('is_blacklisted', '!=', True)],
            ['visitor_id'],
            ['track_id:array_agg']
        )
        track_ids_map = {visitor.id: track_ids for visitor, track_ids in results}
        for visitor in self:
            visitor.event_track_push_enabled_ids = track_ids_map.get(visitor.id, [])

    def _search_event_track_push_enabled_ids(self, operator, operand):
        if operator == "not in":
            raise NotImplementedError(self.env._("Unsupported 'Not In' operation on track push enabled tracks"))

        track_visitors = self.env['event.track.visitor'].sudo().search([
            ('track_id', operator, operand),
            ('is_blacklisted', '=', True)
        ])
        return [('id', 'not in', track_visitors.visitor_id.ids)]
