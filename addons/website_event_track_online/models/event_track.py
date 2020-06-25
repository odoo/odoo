# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class Track(models.Model):
    _name = "event.track"
    _inherit = ['event.track']

    # wishlist / visitors management
    event_track_visitor_ids = fields.One2many(
        'event.track.visitor', 'track_id', string="Track Visitors",
        groups="event.group_event_user")
    is_reminder_on = fields.Boolean('Is Reminder On', compute='_compute_is_reminder_on')
    wishlist_visitor_ids = fields.Many2many(
        'website.visitor', string="Visitor Wishlist",
        compute="_compute_wishlist_visitor_ids", compute_sudo=True,
        search="_search_wishlist_visitor_ids",
        groups="event.group_event_user")
    wishlist_visitor_count = fields.Integer(
        string="# Wishlisted",
        compute="_compute_wishlist_visitor_ids", compute_sudo=True,
        groups="event.group_event_user")
    wishlisted_by_default = fields.Boolean(
        string='Always Wishlisted',
        help="""If set, the talk will be starred for each attendee registered to the event. The attendee won't be able to un-star this talk.""")

    # WISHLIST / VISITOR MANAGEMENT

    @api.depends('wishlisted_by_default', 'event_track_visitor_ids.visitor_id',
                 'event_track_visitor_ids.partner_id', 'event_track_visitor_ids.is_wishlisted',
                 'event_track_visitor_ids.is_blacklisted')
    @api.depends_context('uid')
    def _compute_is_reminder_on(self):
        current_visitor = self.env['website.visitor']._get_visitor_from_request(force_create=False)
        if self.env.user._is_public() and not current_visitor:
            for track in self:
                track.is_reminder_on = track.wishlisted_by_default
        else:
            if self.env.user._is_public():
                domain = [('visitor_id', '=', current_visitor.id)]
            elif current_visitor:
                domain = [
                    '|',
                    ('partner_id', '=', self.env.user.partner_id.id),
                    ('visitor_id', '=', current_visitor.id)
                ]
            else:
                domain = [('partner_id', '=', self.env.user.partner_id.id)]

            event_track_visitors = self.env['event.track.visitor'].sudo().search_read(
                expression.AND([
                    domain,
                    [('track_id', 'in', self.ids)]
                ]), fields=['track_id', 'is_wishlisted', 'is_blacklisted']
            )

            wishlist_map = {
                track_visitor['track_id'][0]: {
                    'is_wishlisted': track_visitor['is_wishlisted'],
                    'is_blacklisted': track_visitor['is_blacklisted']
                } for track_visitor in event_track_visitors
            }
            for track in self:
                if wishlist_map.get(track.id):
                    track.is_reminder_on = wishlist_map.get(track.id)['is_wishlisted'] or (track.wishlisted_by_default and not wishlist_map[track.id]['is_blacklisted'])
                else:
                    track.is_reminder_on = track.wishlisted_by_default

    @api.depends('event_track_visitor_ids.visitor_id', 'event_track_visitor_ids.is_wishlisted')
    def _compute_wishlist_visitor_ids(self):
        results = self.env['event.track.visitor'].read_group(
            [('track_id', 'in', self.ids), ('is_wishlisted', '=', True)],
            ['track_id', 'visitor_id:array_agg'],
            ['track_id']
        )
        visitor_ids_map = {result['track_id'][0]: result['visitor_id'] for result in results}
        for track in self:
            track.wishlist_visitor_ids = visitor_ids_map.get(track.id, [])
            track.wishlist_visitor_count = len(visitor_ids_map.get(track.id, []))

    def _search_wishlist_visitor_ids(self, operator, operand):
        if operator == "not in":
            raise NotImplementedError("Unsupported 'Not In' operation on track wishlist visitors")

        track_visitors = self.env['event.track.visitor'].sudo().search([
            ('visitor_id', operator, operand),
            ('is_wishlisted', '=', True)
        ])
        return [('id', 'in', track_visitors.track_id.ids)]

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _get_event_track_visitors(self, force_create=False):
        self.ensure_one()

        force_visitor_create = self.env.user._is_public()
        visitor_sudo = self.env['website.visitor']._get_visitor_from_request(force_create=force_visitor_create)
        if visitor_sudo:
            visitor_sudo._update_visitor_last_visit()

        if self.env.user._is_public():
            domain = [('visitor_id', '=', visitor_sudo.id)]
        elif visitor_sudo:
            domain = [
                '|',
                ('partner_id', '=', self.env.user.partner_id.id),
                ('visitor_id', '=', visitor_sudo.id)
            ]
        else:
            domain = [('partner_id', '=', self.env.user.partner_id.id)]

        track_visitors = self.env['event.track.visitor'].sudo().search(
            expression.AND([domain, [('track_id', 'in', self.ids)]])
        )
        missing = self - track_visitors.track_id
        if missing and force_create:
            track_visitors += self.env['event.track.visitor'].sudo().create([{
                'visitor_id': visitor_sudo.id,
                'partner_id': self.env.user.partner_id.id if not self.env.user._is_public() else False,
                'track_id': track.id,
            } for track in missing])

        return track_visitors
