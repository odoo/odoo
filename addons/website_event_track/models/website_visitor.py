# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteVisitor(models.Model):
    _name = 'website.visitor'
    _inherit = ['website.visitor']

    event_track_visitor_ids = fields.One2many(
        'event.track.visitor', 'visitor_id', string="Track Visitors",
        groups='event.group_event_user')
    event_track_wishlisted_ids = fields.Many2many(
        'event.track', string="Wishlisted Tracks",
        compute="_compute_event_track_wishlisted_ids", compute_sudo=True,
        search="_search_event_track_wishlisted_ids",
        groups="event.group_event_user")
    event_track_wishlisted_count = fields.Integer(
        string="# Wishlisted",
        compute="_compute_event_track_wishlisted_ids", compute_sudo=True,
        groups='event.group_event_user')

    @api.depends('parent_id', 'event_track_visitor_ids.track_id', 'event_track_visitor_ids.is_wishlisted')
    def _compute_event_track_wishlisted_ids(self):
        # include parent's track visitors in a visitor o2m field. We don't add
        # child one as child should not have track visitors (moved to the parent)
        all_visitors = self + self.parent_id
        results = self.env['event.track.visitor'].read_group(
            [('visitor_id', 'in', all_visitors.ids), ('is_wishlisted', '=', True)],
            ['visitor_id', 'track_id:array_agg'],
            ['visitor_id']
        )
        track_ids_map = {result['visitor_id'][0]: result['track_id'] for result in results}
        for visitor in self:
            visitor_track_ids = track_ids_map.get(visitor.id, [])
            parent_track_ids = track_ids_map.get(visitor.parent_id.id, [])
            visitor.event_track_wishlisted_ids = visitor_track_ids + [track_id for track_id in parent_track_ids if track_id not in visitor_track_ids]
            visitor.event_track_wishlisted_count = len(visitor.event_track_wishlisted_ids)

    def _search_event_track_wishlisted_ids(self, operator, operand):
        """ Search visitors with terms on wishlisted tracks. E.g. [('event_track_wishlisted_ids',
        'in', [1, 2])] should return visitors having wishlisted tracks 1, 2 as
        well as their children for notification purpose. """
        if operator == "not in":
            raise NotImplementedError("Unsupported 'Not In' operation on track wishlist visitors")

        track_visitors = self.env['event.track.visitor'].sudo().search([
            ('track_id', operator, operand),
            ('is_wishlisted', '=', True)
        ])
        if track_visitors:
            visitors = track_visitors.visitor_id
            # search children, even archived one, to contact them
            children = self.env['website.visitor'].with_context(
                active_test=False
            ).sudo().search([('parent_id', 'in', visitors.ids)])
            visitor_ids = (visitors + children).ids
        else:
            visitor_ids = []

        return [('id', 'in', visitor_ids)]

    def _link_to_partner(self, partner, update_values=None):
        """ Propagate partner update to track_visitor records """
        if partner:
            track_visitor_wo_partner = self.event_track_visitor_ids.filtered(lambda track_visitor: not track_visitor.partner_id)
            if track_visitor_wo_partner:
                track_visitor_wo_partner.partner_id = partner
        super(WebsiteVisitor, self)._link_to_partner(partner, update_values=update_values)

    def _link_to_visitor(self, target, keep_unique=True):
        """ Override linking process to link wishlist to the final visitor. """
        self.event_track_visitor_ids.visitor_id = target.id
        return super(WebsiteVisitor, self)._link_to_visitor(target, keep_unique=keep_unique)
