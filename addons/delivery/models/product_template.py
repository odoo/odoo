# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

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
