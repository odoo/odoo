# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    property_product_pricelist = fields.Many2one(
        'product.pricelist', 'Sale Pricelist', company_dependent=True,
        help="This pricelist will be used, instead of the default one, for sales to the current partner")

    def _commercial_fields(self):
        return super(Partner, self)._commercial_fields() + ['property_product_pricelist']
