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
    print_packaging_labels = fields.Boolean(default=True)

    def _get_report_template(self):
        if 'zpl' in self.print_format:
            return 'stock.label_product_product'
        return super()._get_report_template()

    def _get_quantity_by_packaging(self):
        if not self.print_packaging_labels or not self.move_ids:
            return super()._get_quantity_by_packaging()

        moves_with_packaging = self.move_ids.filtered(lambda mv: mv.product_packaging_id)
        quantity_by_packaging = defaultdict(int)
        for move in moves_with_packaging:
            if self.move_quantity == 'custom':
                quantity_by_packaging[move.product_packaging_id.id] += self.custom_quantity
            elif move.product_packaging_qty:
                quantity_by_packaging[move.product_packaging_id.id] += move.product_packaging_qty
        return {'quantity_by_packaging': quantity_by_packaging}

    def _get_quantity_by_product(self):
        if self.move_quantity != 'move':
            return super()._get_quantity_by_product()

        product_quantities = defaultdict(int)
        moves_without_packaging = self.move_ids.filtered(lambda mv: not mv.product_packaging_id)
        uom_unit = self.env.ref('uom.product_uom_categ_unit', raise_if_not_found=False)
        no_move_lines_done = all(float_is_zero(ml.quantity, precision_rounding=ml.product_uom_id.rounding) for ml in moves_without_packaging.move_line_ids)

        if self.move_quantity == 'move' and moves_without_packaging and no_move_lines_done:
            for move in moves_without_packaging:
                if move.product_uom.category_id == uom_unit:
                    use_reserved = float_compare(move.quantity, 0, precision_rounding=move.product_uom.rounding) > 0
                    useable_qty = move.quantity if use_reserved else move.product_uom_qty
                    if not float_is_zero(useable_qty, precision_rounding=move.product_uom.rounding):
                        product_quantities[move.product_id.id] += useable_qty
            quantity_by_product = {p: int(q) for p, q in product_quantities.items()}
            return {'quantity_by_product': quantity_by_product}
        elif self.move_quantity == 'move' and moves_without_packaging.move_line_ids:
            # Pass only products with some quantity done to the report
            custom_barcodes = defaultdict(list)
            for line in moves_without_packaging.move_line_ids:
                if line.product_uom_id.category_id == uom_unit:
                    if (line.lot_id or line.lot_name) and int(line.quantity):
                        custom_barcodes[line.product_id.id].append(('product', line.lot_id.name or line.lot_name, int(line.quantity)))
                        continue
                    product_quantities[line.product_id.id] += line.quantity
                else:
                    product_quantities[line.product_id.id] = 1
            return {
                'quantity_by_product': {p: int(q) for p, q in product_quantities.items() if q},
                'custom_barcodes': custom_barcodes,
            }
        return {}
