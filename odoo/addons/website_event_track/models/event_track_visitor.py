# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TrackVisitor(models.Model):
    """ Table linking track and visitors. """
    _name = 'event.track.visitor'
    _description = 'Track / Visitor Link'
    _table = 'event_track_visitor'
    _rec_name = 'track_id'
    _order = 'track_id'

    partner_id = fields.Many2one(
        'res.partner', string='Partner', compute='_compute_partner_id',
        index=True, ondelete='set null', readonly=False, store=True)
    visitor_id = fields.Many2one(
        'website.visitor', string='Visitor', index=True, ondelete='cascade')
    track_id = fields.Many2one(
        'event.track', string='Track',
        index=True, required=True, ondelete='cascade')
    is_wishlisted = fields.Boolean(string="Is Wishlisted")
    is_blacklisted = fields.Boolean(string="Is reminder off", help="As key track cannot be un-favorited, this field store the partner choice to remove the reminder for key tracks.")

    @api.depends('visitor_id')
    def _compute_partner_id(self):
        for track_visitor in self:
            if track_visitor.visitor_id.partner_id and not track_visitor.partner_id:
                track_visitor.partner_id = track_visitor.visitor_id.partner_id
            elif not track_visitor.partner_id:
                track_visitor.partner_id = False
