# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_product_pricelist = fields.Many2one('product.pricelist', company_dependent=True,
        domain=[('type', '=', 'sale')], string="Sale Pricelist",
        help="This pricelist will be used, instead of the default one, for sales to the current partner")

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + ['property_product_pricelist']
