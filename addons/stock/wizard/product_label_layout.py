# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    move_ids = fields.Many2many('stock.move')
    print_packaging = fields.Boolean(
        'Print Packaging',
        help="Print labels with each delivery order line's packaging.",
    )
    move_quantity = fields.Selection([
        ('move', 'Operation Quantities'),
        ('custom', 'Custom')], string="Quantity to print", required=True, default='custom')

    def _get_move_label_packaging(self, move):
        return move.packaging_uom_id if self.print_packaging else self.env['uom.uom']

    def _save_user_defaults(self):
        super()._save_user_defaults()
        self.env['ir.default'].sudo().set(self._name, 'print_packaging', self.print_packaging, user_id=self.env.uid)

    def _get_label_requests(self):
        if not self.move_ids:
            return super()._get_label_requests()

        if self.move_quantity == 'custom':
            if not self.print_packaging:
                return super()._get_label_requests()
            return [{
                'product': move.product_id,
                'barcode_value': self._get_packaging_barcode(move.product_id, self._get_move_label_packaging(move)),
                'copies': self.custom_quantity,
                'packaging': self._get_move_label_packaging(move),
            } for move in self.move_ids]

        if self.print_packaging:
            return [{
                'product': move.product_id,
                'barcode_value': self._get_packaging_barcode(move.product_id, move.packaging_uom_id),
                'copies': int(move.packaging_uom_qty),
                'packaging': move.packaging_uom_id,
            } for move in self.move_ids if move.packaging_uom_qty]

        quantities = defaultdict(int)
        label_requests = []
        move_lines = self.move_ids.move_line_ids
        if all(line.uom_id.is_zero(line.quantity) for line in move_lines):
            for move in self.move_ids:
                use_reserved = move.uom_id.compare(move.quantity, 0) > 0
                quantity = move.quantity if use_reserved else move.product_uom_qty
                if move.uom_id.is_zero(quantity):
                    continue
                quantities[move.product_id] += quantity
        else:
            uom_unit = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
            for line in move_lines:
                if line.uom_id._has_common_reference(uom_unit):
                    if (line.lot_id or line.lot_name) and int(line.quantity):
                        label_requests.append({
                            'product': line.product_id,
                            'barcode_value': line.lot_id.name or line.lot_name,
                            'copies': int(line.quantity),
                            'packaging': self.env['uom.uom'],
                        })
                    else:
                        quantities[line.product_id] += line.quantity
                else:
                    quantities[line.product_id] = 1

        return [{
            'product': product,
            'barcode_value': product.barcode or '',
            'copies': int(quantity),
            'packaging': self.env['uom.uom'],
        } for product, quantity in quantities.items() if quantity] + label_requests
