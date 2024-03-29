# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(
        self, product_id=None, line_id=None,
        linked_line_id=False, optional_product_ids=None, **kwargs
    ):
        lines = super()._cart_find_product_line(product_id, line_id, **kwargs)
        if line_id:  # in this case we get the exact line we want, so filtering below would be wrong
            return lines

        lines = lines.filtered(lambda line: line.linked_line_id.id == linked_line_id)
        if optional_product_ids:
            # only match the lines with the same chosen optional products on the existing lines
            lines = lines.filtered(lambda line: optional_product_ids == set(line.option_line_ids.product_id.id))
        else:
            lines = lines.filtered(lambda line: not line.option_line_ids)

        return lines
