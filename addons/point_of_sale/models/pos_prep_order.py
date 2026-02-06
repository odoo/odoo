from odoo import fields, models, api
from uuid import uuid4
import json


class PosPrepOrder(models.Model):
    _name = 'pos.prep.order'
    _description = 'Pos Preparation Order'
    _inherit = ['pos.load.mixin']

    pos_order_id = fields.Many2one('pos.order', string='Order', ondelete='cascade', index='btree_not_null')
    prep_line_ids = fields.One2many('pos.prep.line', 'prep_order_id', string='Preparation Lines')
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('pos_order_id', 'in', [order['id'] for order in data['pos.order']])]

    @api.model
    def _generate_line_key(self, line):
        object_key = {
            "product_id": line.product_id.id,
            "combo_parent_id": line.combo_parent_id.id,
            "combo_line_ids": sorted(line.combo_line_ids.ids),
            "attribute_value_ids": sorted(line.attribute_value_ids.ids),
            "note": line.note if hasattr(line, 'note') else "",
            "customer_note": line.customer_note if hasattr(line, 'customer_note') else "",
        }
        return json.dumps(object_key)

    @api.model
    def update_last_order_change(self, order):
        """
        This method is use to create order changes for orders than was
        created from a self ordering device. Indeed, those orders
        are not created from the PoS itself, so no change is created.
        """
        prep_lines_by_key = {}
        prep_order = self.env['pos.prep.order'].create({
            'pos_order_id': order.id,
        })

        for line in order.prep_order_ids.prep_line_ids:
            key = self._generate_line_key(line.pos_order_line_id or line)

            if not prep_lines_by_key.get(key):
                prep_lines_by_key[key] = {
                    'quantity': 0,
                    'lines': [],
                }

            quantity = line.quantity - line.cancelled
            prep_lines_by_key[key]['quantity'] += quantity
            prep_lines_by_key[key]['lines'].append(line)

        for line in order.lines:
            key = self._generate_line_key(line)
            quantity = abs(line.qty)
            remaining_qty = prep_lines_by_key.get(key, {}).get('quantity', 0)

            if remaining_qty > 0:
                deductable_qty = min(remaining_qty, quantity)
                quantity -= deductable_qty
                prep_lines_by_key[key]['quantity'] -= deductable_qty

            if quantity == 0:
                continue

            self.env['pos.prep.line'].create({
                'quantity': line.qty,
                'prep_order_id': prep_order.id,
                'pos_order_line_id': line.id,
            })

        for key, prep_lines in prep_lines_by_key.items():
            if prep_lines['quantity'] <= 0:
                continue

            for line in reversed(prep_lines['lines']):
                cancellable_qty = line.quantity - line.cancelled
                if cancellable_qty == 0:
                    continue

                deductable_qty = min(cancellable_qty, prep_lines['quantity'])
                line.cancelled += deductable_qty
                prep_lines['quantity'] -= deductable_qty

                if prep_lines['quantity'] == 0:
                    break
