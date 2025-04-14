# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class LoyaltyPointTrack(models.Model):
    _name = 'loyalty.point.track'
    _description = 'Tracks allocation of loyalty points from issuers to redeemers'

    issuer_line_id = fields.Many2one(
        string='Issuer History Line',
        comodel_name='loyalty.history',
        ondelete='cascade',
    )
    redeemer_line_id = fields.Many2one(
        string='Redeemer History Line',
        comodel_name='loyalty.history',
        ondelete='cascade',
    )
    points = fields.Float(string='Points')
