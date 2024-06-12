# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models
from odoo.tools import float_compare, float_is_zero


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    move_ids = fields.Many2many('stock.move')
    move_quantity = fields.Selection([
        ('move', 'Operation Quantities'),
        ('custom', 'Custom')], string="Quantity to print", required=True, default='custom')
    print_format = fields.Selection(selection_add=[
        ('zpl', 'ZPL Labels'),
        ('zplxprice', 'ZPL Labels with price')
    ], ondelete={'zpl': 'set default', 'zplxprice': 'set default'})
    packaging_labels = fields.Boolean(default=True)

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()

        if 'zpl' in self.print_format:
            xml_id = 'stock.label_product_product'

        product_quantities = defaultdict(int)
        uom_unit = self.env.ref('uom.product_uom_categ_unit', raise_if_not_found=False)
        if self.move_quantity == 'move' and self.move_ids and all(float_is_zero(ml.quantity, precision_rounding=ml.product_uom_id.rounding) for ml in self.move_ids.move_line_ids):
            for move in self.move_ids:
                if move.product_uom.category_id == uom_unit:
                    use_reserved = float_compare(move.quantity, 0, precision_rounding=move.product_uom.rounding) > 0
                    useable_qty = move.quantity if use_reserved else move.product_uom_qty
                    if not float_is_zero(useable_qty, precision_rounding=move.product_uom.rounding):
                        product_quantities[move.product_id.id] += useable_qty
            data['quantity_by_product'] = {p: int(q) for p, q in product_quantities.items()}
        elif self.move_quantity == 'move' and self.move_ids.move_line_ids:
            custom_barcodes = defaultdict(list)
            for line in self.move_ids.move_line_ids:
                if line.product_uom_id.category_id == uom_unit:
                    if (line.lot_id or line.lot_name) and int(line.quantity):
                        custom_barcodes[line.product_id.id].append((line.lot_id.name or line.lot_name, int(line.quantity)))
                        continue
                    product_quantities[line.product_id.id] += line.quantity
                else:
                    product_quantities[line.product_id.id] = 1
            # Pass only products with some quantity done to the report
            data['quantity_by_product'] = {p: int(q) for p, q in product_quantities.items() if q}
            data['custom_barcodes'] = custom_barcodes

        if self.packaging_labels:
            packaging_quantities = defaultdict(int)
            for move in self.move_ids:
                if move.product_packaging_id:
                    data['quantity_by_product'].pop(move.product_id.id, None)
                    packaging_quantities[move.product_packaging_id.id] += move.product_uom_qty / move.product_packaging_id.qty
            data['quantity_by_packaging'] = {p: int(q if self.move_quantity == 'move' else self.custom_quantity) for p, q in packaging_quantities.items() if q}

        return xml_id, data
