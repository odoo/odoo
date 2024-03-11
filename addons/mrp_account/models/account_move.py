# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from collections import defaultdict


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_invoiced_qty_per_product(self):
        # Replace the kit-type products with their components
        qties = defaultdict(float)
        res = super()._get_invoiced_qty_per_product()
        invoiced_products = self.env['product.product'].concat(*res.keys())
        bom_kits = self.env['mrp.bom']._bom_find(invoiced_products, company_id=self.company_id[:1].id, bom_type='phantom')
        for product, qty in res.items():
            bom_kit = bom_kits[product]
            if bom_kit:
                invoiced_qty = product.uom_id._compute_quantity(qty, bom_kit.product_uom_id, round=False)
                factor = invoiced_qty / bom_kit.product_qty
                dummy, bom_sub_lines = bom_kit.explode(product, factor)
                for bom_line, bom_line_data in bom_sub_lines:
                    qties[bom_line.product_id] += bom_line.product_uom_id._compute_quantity(bom_line_data['qty'], bom_line.product_id.uom_id)
            else:
                qties[product] += qty
        return qties
