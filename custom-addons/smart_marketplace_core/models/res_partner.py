# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_marketplace_seller = fields.Boolean(
        string='Is Marketplace Seller',
        default=False,
        help='Check this if this partner is a marketplace seller',
    )
    marketplace_seller_ids = fields.One2many(
        'marketplace.seller',
        'partner_id',
        string='Marketplace Seller Account',
    )
