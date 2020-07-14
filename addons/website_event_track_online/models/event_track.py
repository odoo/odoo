# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools.mail import is_html_empty
from odoo.modules.module import get_resource_path


class Track(models.Model):
    _name = "event.track"
    _inherit = ['event.track']

    # status management
    is_accepted = fields.Boolean('Is Accepted', related='stage_id.is_accepted', readonly=True)
    # speaker
    partner_biography = fields.Html(
        string='Biography', compute='_compute_partner_biography',
        readonly=False, store=True)
    website_image_url = fields.Char(
        string='Image URL', max_width=256, max_height=256,
        compute='_compute_website_image_url', compute_sudo=True, store=False)
    # wishlist / visitors maanagement
    event_track_visitor_ids = fields.One2many(
        'event.track.visitor', 'track_id', string="Track Visitors",
        groups="event.group_event_user")
    is_reminder_on = fields.Boolean('Is Reminder On', compute='_compute_is_reminder_on')
    wishlist_visitor_ids = fields.Many2many(
        'website.visitor', string="Visitor Wishlist",
        compute="_compute_wishlist_track_visitors", compute_sudo=True,
        search="_search_wishlist_visitor_ids",
        groups="event.group_event_user")
    wishlist_visitor_count = fields.Integer(
        string="# Wishlisted",
        compute="_compute_wishlist_track_visitors", compute_sudo=True,
        groups="event.group_event_user")
    wishlist_partner_ids = fields.Many2many(
        'res.partner', string="Partner Wishlisted",
        compute="_compute_wishlist_track_partners", compute_sudo=True,
        groups="event.group_event_user")
    wishlist_partner_count = fields.Integer(
        string="# Wishlisted (Partners)",
        compute="_compute_wishlist_track_partners", compute_sudo=True,
        groups="event.group_event_user")
    wishlisted_by_default = fields.Boolean(
        string='Always Wishlisted',
        help="""If set, the talk will be starred for each attendee registered to the event. The attendee won't be able to un-star this talk.""")

    # SPEAKER

    @api.depends('partner_id')
    def _compute_partner_biography(self):
        for track in self:
            if track.partner_id and is_html_empty(track.partner_biography):
                track.partner_biography = track.partner_id.website_description

    @api.depends('image', 'partner_id.image_256')
    def _compute_website_image_url(self):
        for track in self:
            if track.image:
                track.website_image_url = self.env['website'].image_url(track, 'image', size=256)
            elif track.partner_id.image_256:
                track.website_image_url = self.env['website'].image_url(track.partner_id, 'image_256', size=256)
            else:
                track.website_image_url = get_resource_path('website_event_track', 'static/src/img', 'event_track_default_%d.png' % (track.id % 2))

    # WISHLIST / VISITOR MANAGEMENT

    @api.depends('event_track_visitor_ids.visitor_id', 'event_track_visitor_ids.partner_id')
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

    @api.depends('event_track_visitor_ids.visitor_id')
    def _compute_wishlist_track_visitors(self):
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

    @api.depends('event_track_visitor_ids.partner_id', 'event_track_visitor_ids.is_wishlisted')
    def _compute_wishlist_track_partners(self):
        results = self.env['event.track.visitor'].read_group(
            [('track_id', 'in', self.ids), ('is_wishlisted', '=', True)],
            ['track_id', 'partner_id:array_agg'],
            ['track_id']
        )
        partner_ids_map = {result['track_id'][0]: result['partner_id'] for result in results}
        for track in self:
            track.wishlist_partner_ids = partner_ids_map.get(track.id, [])
            track.wishlist_partner_count = len(partner_ids_map.get(track.id, []))

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _get_event_track_visitors(self, visitor, force_create=False):
        self.ensure_one()

        track_visitors = self.env['event.track.visitor'].sudo().search([
            ('visitor_id', '=', visitor.id),
            ('track_id', 'in', self.ids)
        ])
        missing = self - track_visitors.track_id
        if missing and force_create:
            track_visitors += self.env['event.track.visitor'].sudo().create([{
                'visitor_id': visitor.id,
                'track_id': self.id,
            } for track in missing])

        return track_visitors
