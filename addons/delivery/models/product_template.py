# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hs_code = fields.Char(string="HS Code", help="Standardized code for international shipping and goods declaration", oldname="x_hs_code")

    @api.multi
    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if vals.get('list_price'):
            DeliveryCarrier = self.env['delivery.carrier']
            for template in self:
                carrier = DeliveryCarrier.search([('product_id', 'in', template.product_variant_ids.ids)])
                if carrier:
                    carrier.create_price_rules()
        return res
