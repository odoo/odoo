# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _compute_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        """ Add the price of the subcontracting supplier if it exists with the bom configuration.
        """
        price = super()._compute_bom_price(bom, boms_to_recompute, byproduct_bom)
        if bom and bom.type == 'subcontract':
            seller = self._select_seller(quantity=bom.product_qty, uom_id=bom.product_uom_id, params={'subcontractor_ids': bom.subcontractor_ids})
            if seller:
                seller_price = seller.currency_id._convert(seller.price, self.env.company.currency_id, (bom.company_id or self.env.company), fields.Date.today())
                price += seller.product_uom._compute_price(seller_price, self.uom_id)
        return price
