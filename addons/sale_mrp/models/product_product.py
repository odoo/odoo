# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Product(models.Model):
    _inherit = "product.product"

    def _compute_quantities(self):
        """ When the product is a kit, this override computes the fields :
         - 'virtual_available'
         - 'qty_available'
         - 'incoming_qty'
         - 'outgoing_qty'
         """
        for product in self:
            bom_kit = self.env['mrp.bom']._bom_find(product=product, bom_type='phantom')
            if bom_kit:
                boms, bom_sub_lines = bom_kit.explode(product, 1)
                ratios_virtual_available = []
                ratios_qty_available = []
                ratios_incoming_qty = []
                ratios_outgoing_qty = []
                for bom_line, bom_line_data in bom_sub_lines:
                    component = bom_line.product_id
                    uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                    qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id)
                    ratios_virtual_available.append(component.virtual_available / qty_per_kit)
                    ratios_qty_available.append(component.qty_available / qty_per_kit)
                    ratios_incoming_qty.append(component.incoming_qty / qty_per_kit)
                    ratios_outgoing_qty.append(component.outgoing_qty / qty_per_kit)
                if bom_sub_lines:
                    product.virtual_available = min(ratios_virtual_available) // 1
                    product.qty_available = min(ratios_qty_available) // 1
                    product.incoming_qty = min(ratios_incoming_qty) // 1
                    product.outgoing_qty = min(ratios_incoming_qty) // 1
            else:
                super(Product, self)._compute_quantities()
