# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_website_sale_loyalty = fields.Boolean(default=True)

    has_loyalty = fields.Boolean("Has Loyalty Program", help="Enables a loyalty program for this website",
        related='website_id.has_loyalty', readonly=False)
    loyalty_id = fields.Many2one('loyalty.program', string='Loyalty Program', help='The loyalty program used by this website',
        related='website_id.loyalty_id', readonly=False)
