# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    wishlist_ids = fields.One2many('product.wishlist', 'partner_id', string='Wishlist', domain=[('active', '=', True)])
