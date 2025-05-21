from odoo import fields, models, api
from uuid import uuid4


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
    def update_last_order_change(self, order):
        """
        This method is use to create order changes for orders than was
        created from a self ordering device. Indeed, those orders
        are not created from the PoS itself, so no change is created.
        """
        prep_order = False

        for line in order.lines:
            prep_qty = sum(pl.quantity - pl.cancelled for pl in line.prep_line_ids)
            quantity_diff = line.qty - prep_qty

            if quantity_diff > 0:
                if not prep_order:
                    prep_order = self.env['pos.prep.order'].create({
                        'pos_order_id': order.id,
                    })
                self.env['pos.prep.line'].create({
                    'quantity': quantity_diff,
                    'prep_order_id': prep_order.id,
                    'pos_order_line_id': line.id,
                    'product_id': line.product_id.id,
                    'attribute_value_ids': line.attribute_value_ids.ids,
                })
            elif quantity_diff < 0:
                remaining = -quantity_diff
                for prep_line in reversed(line.prep_line_ids):
                    available = prep_line.quantity - prep_line.cancelled
                    cancel = min(available, remaining)
                    prep_line.cancelled += cancel
                    remaining -= cancel
                    if remaining <= 0:
                        break

        # Cancel all orphaned prep lines (no pos_order_line_id) - e.g. from deleted orderlines
        for prep_line in order.prep_order_ids.prep_line_ids.filtered(lambda l: not l.pos_order_line_id):
            prep_line.cancelled = prep_line.quantity
