# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression


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

    @api.depends('event_track_visitor_ids.track_id', 'event_track_visitor_ids.is_wishlisted')
    def _compute_event_track_wishlisted_ids(self):
        results = self.env['event.track.visitor']._read_group(
            [('visitor_id', 'in', self.ids), ('is_wishlisted', '=', True)],
            ['visitor_id'],
            ['track_id:array_agg'],
        )
        track_ids_map = {visitor.id: track_ids for visitor, track_ids in results}
        for visitor in self:
            visitor.event_track_wishlisted_ids = track_ids_map.get(visitor.id, [])
            visitor.event_track_wishlisted_count = len(visitor.event_track_wishlisted_ids)

    def _search_event_track_wishlisted_ids(self, operator, operand):
        """ Search visitors with terms on wishlisted tracks. E.g. [('event_track_wishlisted_ids',
        'in', [1, 2])] should return visitors having wishlisted tracks 1, 2. """
        if operator == "not in":
            raise NotImplementedError(_("Unsupported 'Not In' operation on track wishlist visitors"))

        track_visitors = self.env['event.track.visitor'].sudo().search([
            ('track_id', operator, operand),
            ('is_wishlisted', '=', True)
        ])

        return [('id', 'in', track_visitors.visitor_id.ids)]

    def _inactive_visitors_domain(self):
        """ Visitors registered to push subscriptions are considered always active and should not be
        deleted. """
        domain = super()._inactive_visitors_domain()
        return expression.AND([domain, [('event_track_visitor_ids', '=', False)]])

    def _merge_visitor(self, target):
        """ Override linking process to link wishlist to the final visitor. """
        self.event_track_visitor_ids.visitor_id = target.id
        track_visitor_wo_partner = self.event_track_visitor_ids.filtered(lambda track_visitor: not track_visitor.partner_id)
        if track_visitor_wo_partner:
            track_visitor_wo_partner.partner_id = target.partner_id
        return super()._merge_visitor(target)
