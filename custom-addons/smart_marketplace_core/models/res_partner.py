# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_marketplace_seller = fields.Boolean(string='Is Marketplace Seller', default=False)
    marketplace_seller_id = fields.One2many(
        'marketplace.seller',
        'partner_id',
        string='Marketplace Seller',
    )

