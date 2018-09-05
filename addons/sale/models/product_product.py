# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sales_count = fields.Integer(compute='_sales_count', string='# Sales')

    def _sales_count(self):
        self._cr.execute("""
        SELECT  l.product_id,
        sum(l.product_uom_qty / u.factor * u2.factor) AS product_uom_qty                    
        FROM sale_order_line l
           JOIN sale_order s ON l.order_id = s.id     
           LEFT JOIN product_product p ON l.product_id = p.id
           LEFT JOIN product_template t ON p.product_tmpl_id = t.id
           LEFT JOIN product_uom u ON u.id = l.product_uom
           LEFT JOIN product_uom u2 ON u2.id = t.uom_id
        WHERE s.state in ('done', 'sale') and product_id in ({product_ids})
        GROUP BY l.product_id""".format(product_ids=", ".join(str(i) for i in self.ids)))
        product_qty = {r[0]: r[1] for r in self._cr.fetchall()}
        for product in self:
            product.sales_count = product_qty.get(product.id, 0)
