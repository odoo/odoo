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

        # Build a map of combo_parent_id -> {child_line: quantity_diff} for children with positive diffs
        children_by_parent = {}
        line_diffs = {}
        for line in order.lines:
            prep_qty = sum(pl.quantity - pl.cancelled for pl in line.prep_line_ids)
            quantity_diff = line.qty - prep_qty
            line_diffs[line.id] = quantity_diff
            if quantity_diff > 0 and line.combo_parent_id:
                children_by_parent.setdefault(line.combo_parent_id.id, []).append(
                    (line, quantity_diff)
                )

        for line in order.lines:
            quantity_diff = line_diffs[line.id]

            if quantity_diff > 0:
                # When split_per_product is enabled, skip combo children here — they are
                # handled inline by their parent's _get_or_create_prep_order_line via
                # children_by_parent. When split_per_product is disabled, each line
                # (including combo children) must be processed individually.
                if not self._is_split_per_product(order) or not line.combo_parent_id:
                    prep_order = self._get_or_create_prep_order(order, line, prep_order)
                    self._get_or_create_prep_order_line(
                        order, line, prep_order, quantity_diff, children_by_parent
                    )
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

    @api.model
    def _get_or_create_prep_order_line(self, order, line, prep_order, quantity_diff, children_by_parent):
        """Create preparation line(s) for the given order line.
        In the base implementation, creates a single prep line with the full quantity.
        Combo children are handled alongside their parent via children_by_parent.
        """
        self.env['pos.prep.line'].create({
            'quantity': quantity_diff,
            'prep_order_id': prep_order.id,
            'pos_order_line_id': line.id,
            'product_id': line.product_id.id,
            'attribute_value_ids': line.attribute_value_ids.ids,
        })

    @api.model
    def _is_split_per_product(self, order):
        return False

    @api.model
    def _get_or_create_prep_order(self, order, line, current_prep_order):
        return current_prep_order or self.env['pos.prep.order'].create({
            'pos_order_id': order.id,
        })
